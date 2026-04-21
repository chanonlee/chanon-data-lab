# LM Studio / 本地模型：`temperature=0` 时出现长重复输出（近似「死循环」）

本文记录在使用 LangChain `ChatOpenAI` 指向本地 LM Studio（OpenAI 兼容接口）、模型为 `qwen/qwen3-vl-4b` 时，将 **`temperature` 设为 `0`** 后出现的现象、原因与调用链说明。

---

## 1. 现象

- **触发条件**：与 `.docs/01_llmchain_basic.ipynb` 中相同的 LLMChain 写法，仅将 `ChatOpenAI(..., temperature=1)` 改为 **`temperature=0`**，其余（如未设置 `max_tokens`）保持默认。
- **表现**：
  - 模型仍能返回 `finish_reason: "stop"`，但在诗歌末尾（或中段）进入 **同一短语的极高频重复**，例如日志中出现的 `…still…` / `…still…` 连续成百上千次。
  - **`completion_tokens` 急剧升高**（示例中可达数千，如 ~5967），请求耗时明显变长，体感上像「停不下来」的真死循环；实际是 **在未限制 `max_tokens` 的情况下持续自回归采样**，直到服务端长度/上下文上限或引擎结束条件触发。
- **对照**：同一提示词下 **`temperature=1`（或未强制 0）** 时，notebook 中的输出为正常长度的诗歌，无尾部刷屏式重复。

---

## 2. 原因说明（为何与 `temperature=0` 强相关）

### 2.1 采样方式

- **`temperature = 0`** 在多数实现中表示 **不进行随机软化分布**，每步近似取 **概率最大的 token**（贪心 / 极低温度采样），解码路径完全由当前条件下 **argmax 的尖峰分布**决定。
- **`temperature > 0`** 会对分布做平滑，有机会 **跳出**「当前上下文下仍略占优势、但人类观感极差」的重复短语，从而打断局部循环。

### 2.2 自回归模型的重复陷阱（repetition / attractor）

- 诗歌等任务末尾常出现停顿、省略号、叠句；一旦上下文已形成 **节律性片段**（如 `still…`），在贪心路径下 **下一步最可能仍是延续同一模式**，形成 **吸引子式** 输出。
- **小体量视觉语言模型（如 4B）**在纯文本创意任务上分布更「尖」，更容易锁死在局部重复；这与「模型体积、训练数据、是否主要为 VL 任务优化」等因素叠加有关，并非 LangChain 单独 bug。

### 2.3 为何「像死循环」：缺少输出上限

- `.docs/01_llmchain_basic.ipynb` 默认 **未设置 `max_tokens`**。在重复模式下，引擎会 **持续生成 token** 直至内部停止条件或长度上限；因此 completion 很长、日志里重复的 `still…` 极多。

---

## 3. 触发代码（摘自并改编自 `01_llmchain_basic.ipynb`）

以下为与 notebook 一致的 LLMChain 示例；**将 `temperature` 改为 `0` 即可稳定复现上述长重复现象**（在所述模型与服务组合下）。

```python
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,   # 复现关键：贪心式采样易锁死重复短语
    model="local",
)

template = """Write a {adjective} poem about {subject}."""
prompt = PromptTemplate(template=template, input_variables=["adjective", "subject"])
llm_chain = LLMChain(prompt=prompt, llm=llm, verbose=True)
llm_chain.predict(adjective="sad", subject="ducks, gooses")
```

LM Studio 侧收到的 HTTP 请求体形态与日志一致，例如：

```json
{
  "messages": [
    {
      "content": "Write a sad poem about ducks, gooses.",
      "role": "user"
    }
  ],
  "model": "local",
  "stream": false,
  "temperature": 0
}
```

---

## 4. 「解释器」侧代码：客户端如何把 `temperature` 送进请求

此处「解释器」指 **发起 HTTP 请求的客户端栈**：LangChain 将 `ChatOpenAI` 的字段组装进 OpenAI 兼容的 **`chat.completions.create`** 参数；其中 **`temperature` 会进入请求体**（在未被子类剔除的前提下）。

在当前环境所用的 `langchain_openai` 实现中，默认调用参数包含 `temperature`，例如 `_default_params` 将 `self.temperature` 放入可序列化字段（节选，行号随包版本可能变化）：

```853:882:/Users/ludan/Downloads/git-repo/chanon-data-lab/.venv_langgraph/lib/python3.9/site-packages/langchain_openai/chat_models/base.py
    @property
    def _default_params(self) -> dict[str, Any]:
        """Get the default parameters for calling OpenAI API."""
        exclude_if_none = {
            ...
            "max_tokens": self.max_tokens,
            ...
            "temperature": self.temperature,
            ...
        }

        return {
            "model": self.model_name,
            "stream": self.streaming,
            **{k: v for k, v in exclude_if_none.items() if v is not None},
            **self.model_kwargs,
        }
```

流程简述：**Notebook → `ChatOpenAI` → OpenAI Python SDK → `POST /v1/chat/completions` → LM Studio → 本地推理引擎**。异常长的重复内容 **在服务端采样循环中生成**；LangChain 仅透传 `temperature`，不会在客户端打断重复。

---

## 5. 缓解建议（实践向）

| 手段 | 说明 |
|------|------|
| **`temperature`** | 不要强制 `0`；常用 **0.7～1.0**，或至少 **小正数**（如 0.3～0.5）以降低锁死概率。 |
| **`max_tokens`** | 对 `ChatOpenAI(..., max_tokens=1024)` 等设置上限，避免单次生成无限拉长。 |
| **`frequency_penalty` / `presence_penalty`** | 若后端支持，可适当增大以抑制重复（效果因引擎而异）。 |
| **`stop`** | 若有明确结束标记可设停止序列（诗歌场景不一定适用）。 |

参考：同仓库 `notebookes/07_langchain.ipynb` 中已有注释，对本地模型使用 **`max_tokens`** 与 **`request_timeout`** 限制长请求与重复输出问题。

---

## 6. 小结

- **现象**：`temperature=0` + 未限制长度时，本地 `qwen3-vl-4b` 易出现 **尾部短语海量重复**，`completion_tokens` 暴增。
- **主因**：**贪心式解码**易落入自回归 **重复吸引子**；叠加 **无 `max_tokens`** 则输出可拉得极长。
- **客户端**：LangChain **`ChatOpenAI._default_params`** 将 **`temperature` 原样传入** OpenAI 兼容接口；需在 **采样参数与长度** 上自行约束。

---

*文档日期：2026-04-18*
