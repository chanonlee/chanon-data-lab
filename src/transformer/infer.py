"""
推理与翻译：加载 checkpoint，对单句或 batch 进行解码预测。
"""
import sys
from pathlib import Path

import torch

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models import Transformer


def load_checkpoint(ckpt_path: str, device: torch.device = None):
    """
    加载训练保存的 checkpoint。
    返回: (model, src_vocab, src_idx2word, tgt_vocab, tgt_idx2word, config)
    """
    path = Path(ckpt_path)
    if not path.is_absolute():
        cwd_path = Path.cwd() / path
        path = cwd_path if cwd_path.exists() else _ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint 不存在: {path}")
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    config = ckpt["config"]
    model_cfg = config["model"]
    model = Transformer(
        src_vocab_size=ckpt["src_vocab_size"],
        tgt_vocab_size=ckpt["tgt_vocab_size"],
        d_model=model_cfg["d_model"],
        d_ff=model_cfg["d_ff"],
        n_heads=model_cfg["n_heads"],
        n_layers=model_cfg["n_layers"],
        dropout=model_cfg.get("dropout", 0.1),
        max_len=model_cfg.get("max_len", 5000),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    return (
        model,
        ckpt["src_vocab"],
        ckpt["src_idx2word"],
        ckpt["tgt_vocab"],
        ckpt["tgt_idx2word"],
        config,
    )


def translate(
    model: Transformer,
    enc_input: torch.Tensor,
    tgt_len: int,
    start_symbol: int,
    tgt_idx2word: dict,
    device: torch.device,
    eos_id: int = None,
) -> list:
    """
    自回归解码：每次预测下一个 token，直到 tgt_len 步或遇到 EOS。
    enc_input: (1, src_len)
    返回: 预测的 token id 列表（或对应词列表由调用方转换）。
    """
    if enc_input.dim() == 1:
        enc_input = enc_input.unsqueeze(0)
    enc_input = enc_input.to(device)
    with torch.no_grad():
        enc_outputs, _ = model.encoder(enc_input)
        dec_input = torch.zeros(1, tgt_len, dtype=enc_input.dtype, device=device)
        next_symbol = start_symbol
        for i in range(tgt_len):
            dec_input[0, i] = next_symbol
            dec_outputs, _, _ = model.decoder(dec_input, enc_input, enc_outputs)
            projected = model.projection(dec_outputs)
            prob = projected.squeeze(0).max(dim=-1, keepdim=False)[1]
            next_word = prob[i].item()
            next_symbol = next_word
            if eos_id is not None and next_symbol == eos_id:
                # 去掉起始符 S，不含 EOS
                return [tgt_idx2word.get(dec_input[0, j].item(), "?") for j in range(1, i + 1)]
        # 去掉起始符 S
        return [tgt_idx2word.get(dec_input[0, j].item(), "?") for j in range(1, tgt_len)]


def translate_sentence(
    sentence_tokens: list,
    src_vocab: dict,
    model,
    tgt_len: int,
    tgt_vocab: dict,
    tgt_idx2word: dict,
    device: torch.device,
) -> list:
    """
    输入为已分词的源句 token 列表，转为 id 后调用 translate。
    """
    enc_input = torch.LongTensor([[src_vocab.get(t, 0) for t in sentence_tokens]])
    start_symbol = tgt_vocab.get("S", 1)
    eos_id = tgt_vocab.get("E", 2)
    return translate(
        model, enc_input, tgt_len, start_symbol, tgt_idx2word, device, eos_id
    )


def run_infer(ckpt_path: str = None):
    """示例：加载 checkpoint，对默认第一句做翻译并打印。"""
    if ckpt_path is None:
        ckpt_path = _ROOT / "runs" / "checkpoints" / "transformer_last.pt"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, src_vocab, src_idx2word, tgt_vocab, tgt_idx2word, config = load_checkpoint(
        str(ckpt_path), device
    )
    # 示例：我 是 厨 师 P
    src_tokens = ["我", "是", "厨", "师", "P"]
    tgt_len = 5
    out_words = translate_sentence(
        src_tokens, src_vocab, model, tgt_len, tgt_vocab, tgt_idx2word, device
    )
    print("源句:", " ".join(src_tokens))
    print("译句:", " ".join(out_words))
    return model, src_vocab, tgt_vocab, tgt_idx2word, out_words


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", default=None, help="checkpoint 路径")
    parser.add_argument("--sentence", default=None, help="源句（空格分词），例如: 我 是 厨 师 P")
    args = parser.parse_args()
    ckpt_path = args.ckpt or str(_ROOT / "runs" / "checkpoints" / "transformer_last.pt")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, src_vocab, src_idx2word, tgt_vocab, tgt_idx2word, _ = load_checkpoint(ckpt_path, device)
    if args.sentence:
        tokens = args.sentence.strip().split()
        out = translate_sentence(
            tokens, src_vocab, model, max(5, len(tokens) + 2),
            tgt_vocab, tgt_idx2word, device
        )
        print("源句:", args.sentence)
        print("译句:", " ".join(out))
    else:
        src_tokens = ["我", "是", "厨", "师", "P"]
        out = translate_sentence(
            src_tokens, src_vocab, model, 5, tgt_vocab, tgt_idx2word, device
        )
        print("源句:", " ".join(src_tokens))
        print("译句:", " ".join(out))
