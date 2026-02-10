"""
支持 python -m src.transformer 或直接 python __main__.py 运行训练。
"""
import sys
from pathlib import Path

try:
    from .train import train
except ImportError:
    # 直接运行本文件时没有父包，改为绝对导入
    _root = Path(__file__).resolve().parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from train import train

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # --config 默认是相对路径 "config.yaml"，真实文件位置在 train.load_config() 里解析：
    # 先按「当前工作目录/config.yaml」找，找不到再按「本包目录/config.yaml」（即 src/transformer/config.yaml）
    parser.add_argument("--config", default="config.yaml", help="配置文件路径（相对 cwd 或包目录）")
    parser.add_argument("--data_dir", default=None, help="数据目录（当前未用，数据来自 utils.dataset 内置示例）")
    args = parser.parse_args()
    train(config_path=args.config, data_dir=args.data_dir)
