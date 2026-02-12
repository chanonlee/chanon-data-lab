"""
训练循环：加载配置与数据、训练、使用 WandB / TensorBoard 记录 Loss 与梯度。
"""
import os
import sys
import argparse
from pathlib import Path

# 支持直接运行 python train.py（在 src/transformer 下）
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

try:
    import yaml
except ImportError:
    yaml = None

from models import Transformer
from utils.dataset import (
    load_sentences_from_config,
    build_vocabs_from_sentences,
    make_data,
    TranslationDataset,
)


def load_config(config_path: str) -> dict:
    if yaml is None:
        raise ImportError("请安装 PyYAML: pip install pyyaml")
    path = Path(config_path)
    if not path.is_absolute():
        # 先尝试相对当前工作目录，再尝试相对包目录
        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            path = cwd_path
        else:
            path = _ROOT / path.name
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_loggers(config: dict, run_name: str = None):
    """根据 config 初始化 WandB 和/或 TensorBoard。"""
    log_cfg = config.get("logging", {})
    loggers = {}
    if log_cfg.get("use_wandb"):
        try:
            import wandb
            wandb.init(
                project=log_cfg.get("wandb_project", "transformer-zh-en"),
                entity=log_cfg.get("wandb_entity"),
                name=run_name,
                config=config,
            )
            loggers["wandb"] = wandb
        except ImportError:
            print("未安装 wandb，跳过。pip install wandb")
    if log_cfg.get("use_tensorboard"):
        try:
            from torch.utils.tensorboard import SummaryWriter
            log_dir = log_cfg.get("log_dir", "runs")
            os.makedirs(log_dir, exist_ok=True)
            loggers["tb"] = SummaryWriter(log_dir=log_dir)
        except ImportError:
            print("TensorBoard 需 PyTorch 自带，若仍报错请检查环境。")
    return loggers


def log_scalar(loggers: dict, key: str, value: float, step: int):
    for name, logger in loggers.items():
        if name == "wandb":
            logger.log({key: value}, step=step)
        elif name == "tb":
            logger.add_scalar(key, value, step)


def log_histogram(loggers: dict, key: str, values: torch.Tensor, step: int):
    for name, logger in loggers.items():
        if name == "wandb":
            logger.log({key: logger.Histogram(values.detach().cpu().numpy().ravel())}, step=step)
        elif name == "tb":
            logger.add_histogram(key, values, step)


def train(config_path: str = "config.yaml", data_dir: str = None):

    # 模型参数
    config = load_config(config_path)
    # 设备选择，cuda还是cpu
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 数据：根据 config.data 选择 builtin 或 file
    sentences = load_sentences_from_config(config)

    (
        src_vocab,
        src_idx2word,
        tgt_vocab,
        tgt_idx2word,
        src_vocab_size,
        tgt_vocab_size,
    ) = build_vocabs_from_sentences(sentences)

    # 两边的映射表
    # {'P': 0, '厨': 1, '喜': 2, '学': 3, '师': 4, '我': 5, '教': 6, '是': 7, '欢': 8}
    print(src_vocab)
    # {0: 'P', 1: '厨', 2: '喜', 3: '学', 4: '师', 5: '我', 6: '教', 7: '是', 8: '欢'}
    print(src_idx2word)
    # 9
    print(src_vocab_size)

    # {'P': 0, 'E': 1, 'I': 2, 'S': 3, 'a': 4, 'am': 5, 'cook': 6, 'like': 7, 'teacher': 8, 'teaching': 9}
    print(tgt_vocab)
    # {0: 'P', 1: 'E', 2: 'I', 3: 'S', 4: 'a', 5: 'am', 6: 'cook', 7: 'like', 8: 'teacher', 9: 'teaching'}
    print(tgt_idx2word)
    # 10
    print(tgt_vocab_size)

    enc_inputs, dec_inputs, dec_outputs = make_data(sentences, src_vocab, tgt_vocab)
    dataset = TranslationDataset(enc_inputs, dec_inputs, dec_outputs)
    batch_size = config["training"]["batch_size"]
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 模型
    model_cfg = config["model"]
    model = Transformer(
        src_vocab_size=src_vocab_size,
        tgt_vocab_size=tgt_vocab_size,
        d_model=model_cfg["d_model"],
        d_ff=model_cfg["d_ff"],
        n_heads=model_cfg["n_heads"],
        n_layers=model_cfg["n_layers"],
        dropout=model_cfg.get("dropout", 0.1),
        max_len=model_cfg.get("max_len", 5000),
    ).to(device)

    criterion = nn.CrossEntropyLoss(ignore_index=0)
    train_cfg = config["training"]
    optimizer = optim.SGD(
        model.parameters(),
        lr=train_cfg["lr"],
        momentum=train_cfg.get("momentum", 0.99),
    )

    loggers = get_loggers(config)
    log_cfg = config.get("logging", {})
    log_grad_every = log_cfg.get("log_gradients_every_n_steps", 50)
    epochs = train_cfg["epochs"]
    global_step = 0

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for enc_inputs_b, dec_inputs_b, dec_outputs_b in loader:
            enc_inputs_b = enc_inputs_b.to(device)
            dec_inputs_b = dec_inputs_b.to(device)
            dec_outputs_b = dec_outputs_b.to(device)
            optimizer.zero_grad()
            logits, _, _, _ = model(enc_inputs_b, dec_inputs_b)
            loss = criterion(logits, dec_outputs_b.view(-1))
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
            log_scalar(loggers, "train/loss_step", loss.item(), global_step)
            if log_grad_every and global_step > 0 and global_step % log_grad_every == 0:
                for name, p in model.named_parameters():
                    if p.grad is not None:
                        log_histogram(
                            loggers,
                            f"gradients/{name.replace('.', '/')}",
                            p.grad,
                            global_step,
                        )
            global_step += 1
        mean_loss = epoch_loss / max(n_batches, 1)
        log_scalar(loggers, "train/loss_epoch", mean_loss, epoch)
        if "wandb" in loggers or "tb" in loggers:
            print(f"Epoch {epoch + 1}/{epochs}  loss_epoch={mean_loss:.6f}")

    for logger in loggers.values():
        if hasattr(logger, "finish"):
            logger.finish()
        elif hasattr(logger, "close"):
            logger.close()

    # 保存 checkpoint（含词表信息供 infer 使用）
    ckpt_dir = _ROOT / config.get("logging", {}).get("log_dir", "runs") / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / "transformer_last.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": config,
        "src_vocab": src_vocab,
        "src_idx2word": src_idx2word,
        "tgt_vocab": tgt_vocab,
        "tgt_idx2word": tgt_idx2word,
        "src_vocab_size": src_vocab_size,
        "tgt_vocab_size": tgt_vocab_size,
    }, ckpt_path)
    print(f"Checkpoint 已保存: {ckpt_path}")
    return model, src_vocab, src_idx2word, tgt_vocab, tgt_idx2word, config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--data_dir", default=None, help="数据目录（当前使用内置示例）")
    args = parser.parse_args()
    train(config_path=args.config, data_dir=args.data_dir)
