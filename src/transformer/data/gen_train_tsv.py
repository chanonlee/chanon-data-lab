"""生成 200 行的 data/train.tsv（1 行表头 + 199 条数据）。"""
from pathlib import Path

# 一批可重复使用的平行句对（src, tgt），按空格分词
PAIRS = [
    ("我 是 教 师 P", "I am a teacher"),
    ("我 喜 欢 教 学", "I like teaching P"),
    ("我 是 厨 师 P", "I am a cook"),
    ("我 爱 你 P P", "I love you"),
    ("他 是 学 生 P", "He is a student"),
    ("她 喜 欢 唱 歌", "She likes singing P"),
    ("这 是 一 本 书", "This is a book"),
    ("我 想 喝 水 P", "I want water"),
    ("今 天 很 好 P", "Today is fine"),
    ("我 们 是 朋 友", "We are friends"),
    ("他 是 教 师 P", "He is a teacher"),
    ("她 是 学 生 P", "She is a student"),
    ("我 喜 欢 读 书", "I like reading P"),
    ("他 爱 唱 歌 P", "He loves singing P"),
    ("今 天 天 气 好", "Today is good P"),
    ("这 是 我 的 书", "This is my book"),
    ("我 是 学 生 P", "I am a student"),
    ("她 是 厨 师 P", "She is a cook"),
    ("我 们 喜 欢 学", "We like learning P"),
    ("他 想 喝 水 P", "He wants water P"),
]

def main():
    out = Path(__file__).resolve().parent / "train.tsv"
    n = 199
    with open(out, "w", encoding="utf-8") as f:
        f.write("src\ttgt\n")
        for i in range(n):
            src, tgt = PAIRS[i % len(PAIRS)]
            f.write(f"{src}\t{tgt}\n")
    print(f"Wrote {out} with 1 header + {n} rows.")

if __name__ == "__main__":
    main()
