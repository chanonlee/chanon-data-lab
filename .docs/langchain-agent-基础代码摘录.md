# LangChain 示例整理（每个文件可独立运行）

本目录下的 `01~08` notebook 已按“单文件独立运行”整理：  
- 每个文件都包含自己的 `import`、模型初始化和示例调用。  
- 运行某个文件时，不需要先执行其他文件。  

## 统一依赖（建议先安装）

```bash
pip install -U langchain langchain-openai langchain-community wikipedia tiktoken
```

> 默认使用 LM Studio（OpenAI 兼容接口）：`http://127.0.0.1:1234/v1`。  
> 如果你使用其他兼容服务，可改 `base_url` 与 `model`。

---

## 01) Agent ReAct（工具调用）

```python
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
)

tools = load_tools(["llm-math", "wikipedia"], llm=llm)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    verbose=True,
)
agent.invoke("Five minus three equals how much")
```

## 02) ConversationChain + BufferMemory

```python
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
)

conversation_with_memory = ConversationChain(
    llm=llm,
    memory=ConversationBufferMemory(),
    verbose=True,
)

conversation_with_memory.predict(input="你好，我是 Kevin")
conversation_with_memory.predict(input="我是一个人工智能大模型爱好者")
conversation_with_memory.predict(input="请根据我的信息帮我起一个公众号名称")
```

## 03) Token 计数适配器（可单独验证）

```python
import tiktoken
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

def _count_tokens_with_tiktoken(messages: list) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    n = 0
    for m in messages:
        n += 3
        content = getattr(m, "content", None) or ""
        if isinstance(content, str):
            n += len(enc.encode(content))
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    n += len(enc.encode(part.get("text", "")))
                elif isinstance(part, str):
                    n += len(enc.encode(part))
    return n

class ChatOpenAIWithTokenCount(ChatOpenAI):
    def get_num_tokens_from_messages(self, messages: list, **kwargs) -> int:
        return _count_tokens_with_tiktoken(messages)

# 本地自测（不请求模型）
msgs = [HumanMessage(content="你好"), AIMessage(content="你好，有什么可以帮你？")]
print("estimated tokens =", _count_tokens_with_tiktoken(msgs))
```

## 04) ConversationBufferWindowMemory

```python
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(base_url=LM_STUDIO_BASE, api_key="lm-studio", temperature=0, model="local")

memory_window = ConversationBufferWindowMemory(k=2)
chain_window = ConversationChain(llm=llm, memory=memory_window, verbose=True)

chain_window.predict(input="我叫小明")
chain_window.predict(input="我喜欢跑步")
chain_window.predict(input="我也很喜欢散步")
chain_window.predict(input="我叫什么名字？")
```

## 05) ConversationSummaryBufferMemory（独立版）

```python
MAX_TOKEN_LIMIT = 2048

import tiktoken
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain

def _count_tokens_with_tiktoken(messages: list) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    n = 0
    for m in messages:
        n += 3
        content = getattr(m, "content", None) or ""
        if isinstance(content, str):
            n += len(enc.encode(content))
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    n += len(enc.encode(part.get("text", "")))
                elif isinstance(part, str):
                    n += len(enc.encode(part))
    return n

class ChatOpenAIWithTokenCount(ChatOpenAI):
    def get_num_tokens_from_messages(self, messages: list, **kwargs) -> int:
        return _count_tokens_with_tiktoken(messages)

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAIWithTokenCount(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
)

memory_summary = ConversationSummaryBufferMemory(llm=llm, max_token_limit=MAX_TOKEN_LIMIT)
chain_summary = ConversationChain(llm=llm, memory=memory_summary, verbose=True)
chain_summary.predict(input="我是产品经理，负责 APP 设计")
```

## 06) ConversationTokenBufferMemory（独立版）

```python
MAX_TOKEN_LIMIT = 2048

import tiktoken
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationTokenBufferMemory
from langchain.chains import ConversationChain

def _count_tokens_with_tiktoken(messages: list) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    n = 0
    for m in messages:
        n += 3
        content = getattr(m, "content", None) or ""
        if isinstance(content, str):
            n += len(enc.encode(content))
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    n += len(enc.encode(part.get("text", "")))
                elif isinstance(part, str):
                    n += len(enc.encode(part))
    return n

class ChatOpenAIWithTokenCount(ChatOpenAI):
    def get_num_tokens_from_messages(self, messages: list, **kwargs) -> int:
        return _count_tokens_with_tiktoken(messages)

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAIWithTokenCount(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
)

memory_token = ConversationTokenBufferMemory(llm=llm, max_token_limit=MAX_TOKEN_LIMIT)
chain_token = ConversationChain(llm=llm, memory=memory_token, verbose=True)
chain_token.predict(input="今天天气不错")
```

## 07) LLMChain 基础

```python
from langchain.chains import LLMChain
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
)

template = "Write a {adjective} poem about {subject}."
prompt = PromptTemplate(template=template, input_variables=["adjective", "subject"])
llm_chain = LLMChain(prompt=prompt, llm=llm, verbose=True)
llm_chain.predict(adjective="sad", subject="ducks")
```

## 08) SimpleSequentialChain 基础

```python
from langchain.chains import LLMChain, SimpleSequentialChain
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
llm = ChatOpenAI(
    base_url=LM_STUDIO_BASE,
    api_key="lm-studio",
    temperature=0,
    model="local",
    request_timeout=120,
    max_tokens=1024,
)

cate_template = "你现在是一位美食博主，需要根据用户输入的城市：{city} ，给出对应的美食推荐"
cate_prompt = PromptTemplate(template=cate_template, input_variables=["city"])
cate_chain = LLMChain(llm=llm, prompt=cate_prompt)

intro_template = "你现在是一位美食博主，需要根据用户输入的美食信息：{cate}，给出对应的美食简单介绍"
intro_prompt = PromptTemplate(template=intro_template, input_variables=["cate"])
intro_chain = LLMChain(llm=llm, prompt=intro_prompt)

result_chain = SimpleSequentialChain(chains=[cate_chain, intro_chain], verbose=True)
result_chain.run("成都")
```
