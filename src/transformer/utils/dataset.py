"""
分词、词表、Padding 与 Dataset。支持内置数据与从文件加载。
"""
from pathlib import Path
import torch
from torch import LongTensor
from torch.utils.data import Dataset
from typing import List, Tuple, Dict, Optional, Any


# 特殊 token
PAD = "P"
BOS = "S"
EOS = "E"


def load_sentences_from_file(
    path: str,
    encoding: str = "utf-8",
    delimiter: str = "\t",
) -> List[List[str]]:
    """
    从 TSV/CSV 加载平行句对，返回与 get_default_sentences() 相同格式的列表。

    文件有两种格式（首行为表头，会被跳过）：
    - 2 列：src, tgt → 自动生成 dec_input = "S " + tgt, dec_output = tgt + " E"
    - 3 列：src, dec_input, dec_output → 直接使用
    """
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / path
    if not resolved.exists():
        raise FileNotFoundError(f"数据文件不存在: {resolved}")

    rows: List[List[str]] = []
    with open(resolved, "r", encoding=encoding, newline="") as f:
        lines = [line.rstrip("\n\r") for line in f if line.strip()]
    if not lines:
        return rows
    # 表头
    header = lines[0].split(delimiter)
    ncols = len(header)
    for line in lines[1:]:
        parts = line.split(delimiter)
        if len(parts) < 2:
            continue
        if ncols >= 3 and len(parts) >= 3:
            rows.append([parts[0].strip(), parts[1].strip(), parts[2].strip()])
        else:
            src, tgt = parts[0].strip(), parts[1].strip()
            rows.append([src, BOS + " " + tgt, tgt + " " + EOS])
    return rows


def load_sentences_from_config(config: Any) -> List[List[str]]:
    """
    根据 config 中的 data 配置选择数据源，返回 sentences（格式同 get_default_sentences）。
    """
    data_cfg = config.get("data") or {}
    source = data_cfg.get("source", "builtin")
    if source == "builtin":
        return get_default_sentences()
    if source == "file":
        path = data_cfg.get("path")
        if not path:
            raise ValueError("data.source=file 时必须在 config 中设置 data.path")
        encoding = data_cfg.get("encoding", "utf-8")
        delimiter = data_cfg.get("delimiter", "\t")
        return load_sentences_from_file(path, encoding=encoding, delimiter=delimiter)
    raise ValueError(f"不支持的 data.source: {source}，可选 builtin | file")


def get_default_sentences() -> List[List[str]]:
    """
    默认 10 句中译英示例。
    每行为 [源句, 解码器输入(带 S 开头), 解码器输出(带 E 结尾)]，按空格分词。

    编码器输出 = 中文句子的编码结果，是整句的表示。
    编码器做整句映射，一次看完源句得到表示，不存在「预测下一个 token」；
    解码器是逐 token 预测，所以需要拆成「解码器输入」和「解码器输出」
    解码器输出即解码器输入在每一位置上的「下一个 token」（用于算 loss）。

    """
    return [
        ["我 是 教 师 P", "S I am a teacher", "I am a teacher E"],
        ["我 喜 欢 教 学", "S I like teaching P", "I like teaching P E"],
        ["我 是 厨 师 P", "S I am a cook", "I am a cook E"],
        ["我 爱 你 P P", "S I love you", "I love you E"],
        ["他 是 学 生 P", "S He is a student", "He is a student E"],
        ["她 喜 欢 唱 歌", "S She likes singing P", "She likes singing P E"],
        ["这 是 一 本 书", "S This is a book", "This is a book E"],
        ["我 想 喝 水 P", "S I want water", "I want water E"],
        ["今 天 很 好 P", "S Today is fine", "Today is fine E"],
        ["我 们 是 朋 友", "S We are friends", "We are friends E"],
    ]


def build_vocabs_from_sentences(
    sentences: List[List[str]],
) -> Tuple[Dict[str, int], Dict[int, str], Dict[str, int], Dict[int, str], int, int]:
    """
    从 sentences 构建源/目标词表。
    sentences: 每项为 [src_str, dec_input_str, dec_output_str]，按空格分词。

    返回: (src_vocab, src_idx2word, tgt_vocab, tgt_idx2word, src_vocab_size, tgt_vocab_size)
    """
    src_tokens = set()
    tgt_tokens = set()
    for row in sentences:
        src_tokens.update(row[0].split())
        tgt_tokens.update(row[1].split())
        tgt_tokens.update(row[2].split())
    src_tokens = sorted(src_tokens)
    tgt_tokens = sorted(tgt_tokens)
    # PAD 必须为 0，便于 ignore_index=0
    if PAD not in src_tokens:
        src_tokens.insert(0, PAD)
    else:
        src_tokens.remove(PAD)
        src_tokens.insert(0, PAD)
    if PAD not in tgt_tokens:
        tgt_tokens.insert(0, PAD)
    else:
        tgt_tokens.remove(PAD)
        tgt_tokens.insert(0, PAD)
    src_vocab = {t: i for i, t in enumerate(src_tokens)}
    tgt_vocab = {t: i for i, t in enumerate(tgt_tokens)}
    src_idx2word = {i: t for t, i in src_vocab.items()}
    tgt_idx2word = {i: t for t, i in tgt_vocab.items()}
    return (
        src_vocab,
        src_idx2word,
        tgt_vocab,
        tgt_idx2word,
        len(src_vocab),
        len(tgt_vocab),
    )


def make_data(
    sentences: List[List[str]],
    src_vocab: Dict[str, int],
    tgt_vocab: Dict[str, int],
) -> Tuple[torch.LongTensor, torch.LongTensor, torch.LongTensor]:
    """
    将 sentences 转为 enc_inputs, dec_inputs, dec_outputs（LongTensor）。
    不做 padding，由 DataLoader 的 collate_fn 或外部按最大长度 padding。
    """
    enc_inputs, dec_inputs, dec_outputs = [], [], []
    for row in sentences:
        enc_input = [src_vocab[n] for n in row[0].split()]
        dec_input = [tgt_vocab[n] for n in row[1].split()]
        dec_output = [tgt_vocab[n] for n in row[2].split()]
        enc_inputs.append(enc_input)
        dec_inputs.append(dec_input)
        dec_outputs.append(dec_output)
    return enc_inputs, dec_inputs, dec_outputs


def pad_sequences(
    sequences: List[List[int]],
    max_len: Optional[int],
    pad_id: int = 0,
) -> Tuple[torch.LongTensor, int]:
    """
    将变长序列 padding 到 max_len（若 max_len 为 None 则取当前 batch 最大长度）。
    返回 (padded_tensor, actual_max_len)。
    """
    if max_len is None:
        max_len = max(len(s) for s in sequences)
    padded = []
    for seq in sequences:
        pad_len = max_len - len(seq)
        padded.append(seq + [pad_id] * pad_len)
    return torch.LongTensor(padded), max_len


class TranslationDataset(Dataset):
    """
    封装 enc_inputs / dec_inputs / dec_outputs 的 list（未 padding），
    __getitem__ 返回单条；padding 可在 collate_fn 中做。
    """

    def __init__(
        self,
        enc_inputs: List[List[int]],
        dec_inputs: List[List[int]],
        dec_outputs: List[List[int]],
        src_max_len: Optional[int] = None,
        tgt_max_len: Optional[int] = None,
        pad_id: int = 0,
    ):
        self.enc_inputs = enc_inputs
        self.dec_inputs = dec_inputs
        self.dec_outputs = dec_outputs
        # 自动对齐最长
        self.src_max_len = src_max_len or max(len(x) for x in enc_inputs)
        self.tgt_max_len = tgt_max_len or max(len(x) for x in dec_inputs)
        # 补齐的占位符
        self.pad_id = pad_id

    def __len__(self) -> int:
        return len(self.enc_inputs)

    def __getitem__(self, idx: int) -> Tuple[torch.LongTensor, torch.LongTensor, torch.LongTensor]:
        enc = self.enc_inputs[idx]
        dec_in = self.dec_inputs[idx]
        dec_out = self.dec_outputs[idx]
        # 单条 padding 到固定长度（先声明类型再赋值）
        enc_pad: torch.LongTensor
        enc_pad, _ = pad_sequences([enc], self.src_max_len, self.pad_id)
        dec_in_pad: torch.LongTensor
        dec_in_pad, _ = pad_sequences([dec_in], self.tgt_max_len, self.pad_id)
        dec_out_pad: torch.LongTensor
        dec_out_pad, _ = pad_sequences([dec_out], self.tgt_max_len, self.pad_id)
        # 最后整型，去除dim 1的1维数据
        return enc_pad.squeeze(0), dec_in_pad.squeeze(0), dec_out_pad.squeeze(0)


def get_collate_fn(src_max_len: Optional[int], tgt_max_len: Optional[int], pad_id: int = 0):
    """返回一个 collate_fn，在 DataLoader 里对 batch 做 padding。"""

    def collate_fn(batch):
        enc_list = [b[0].tolist() for b in batch]
        dec_in_list = [b[1].tolist() for b in batch]
        dec_out_list = [b[2].tolist() for b in batch]
        enc, _ = pad_sequences(enc_list, src_max_len, pad_id)
        dec_in, _ = pad_sequences(dec_in_list, tgt_max_len, pad_id)
        dec_out, _ = pad_sequences(dec_out_list, tgt_max_len, pad_id)
        return enc, dec_in, dec_out

    return collate_fn
