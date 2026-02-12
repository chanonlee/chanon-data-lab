# Transformer 中译英（工程化）

从 `notebookes/06_pytorch_transformer.ipynb` 拆分为模块化工程，支持配置管理、WandB/TensorBoard 日志与独立训练/推理脚本。

## 目录结构

```
src/transformer/
├── config.yaml       # 模型与训练配置
├── models/
│   ├── __init__.py
│   └── transformer.py # Encoder-Decoder 模型结构
├── utils/
│   ├── __init__.py
│   └── dataset.py    # 分词、词表、Padding、Dataset
├── train.py          # 训练循环与日志
├── infer.py          # 测试与翻译
├── __main__.py       # python -m 入口
└── README.md
```

## 配置 (config.yaml)

- **data**: `source`（`builtin` | `file`）、`path`（文件路径）、`encoding`、`delimiter`
- **model**: `d_model`, `d_ff`, `n_heads`, `n_layers`, `dropout`, `max_len`
- **training**: `lr`, `batch_size`, `epochs`, `momentum`
- **logging**: `use_wandb` / `use_tensorboard`, `wandb_project`, `log_dir`, `log_gradients_every_n_steps`

## 数据源切换

在 `config.yaml` 的 `data` 里设置：

- **`source: builtin`**：使用内置 10 句中译英示例（默认）。
- **`source: file`**：从文件加载。需设置 `data.path`（如 `data/train.tsv`），路径相对当前工作目录。

**文件格式**（首行为表头，会被跳过）：

- **2 列**：`src`, `tgt`（按空格分词）。程序自动生成解码器输入/输出（S + tgt、tgt + E）。
- **3 列**：`src`, `dec_input`, `dec_output`。与内置格式一致，可完全自定义。

示例 `data/train.tsv`（2 列）：

```
src	tgt
我 是 教 师 P	I am a teacher
我 喜 欢 教 学	I like teaching P
```

## 运行方式

### 训练

```bash
cd src/transformer
pip install pyyaml torch  # 可选: wandb, tensorboard
python train.py --config config.yaml
```

或从项目根目录：

```bash
python -m src.transformer --config src/transformer/config.yaml
```

训练会：

- 使用 `config.yaml` 中的超参
- 将 Loss 与（可选）梯度直方图写入 **WandB** 和/或 **TensorBoard**
- 在 `runs/checkpoints/` 下保存 `transformer_last.pt`

### 推理 / 翻译

```bash
cd src/transformer
python infer.py --ckpt runs/checkpoints/transformer_last.pt
python infer.py --sentence "我 是 厨 师 P"
```

## 生命周期工具

- **WandB**：在 `config.yaml` 中设置 `logging.use_wandb: true`，并安装 `wandb`。首次使用需登录。
- **TensorBoard**：设置 `logging.use_tensorboard: true`，训练后执行 `tensorboard --logdir runs` 查看 Loss 曲线与梯度分布。

## 依赖

- PyTorch
- PyYAML（读取 config）
- 可选：wandb、tensorboard（PyTorch 自带）
