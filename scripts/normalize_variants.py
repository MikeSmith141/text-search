#!/usr/bin/env python3
"""全库异体/旧字形清洗 → 通行简体。

用法:
  python3 scripts/normalize_variants.py            # 全活跃库
  python3 scripts/normalize_variants.py data/辽宋金夏/大金国志.txt
  python3 scripts/normalize_variants.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DATA = Path("/root/projects/text-search/data")

# 长词优先（多字映射先做）
MULTI = {
    "撒𪻞": "撒改",
}

# 单字：扩展区 + 日新字体 + 旧字形 + 用户点名
VARIANT_MAP = {
    # CJK Ext
    "㑹": "会",
    "㸃": "点",
    "㡬": "几",
    "䟽": "疏",
    "䧟": "陷",
    "㮚": "栗",
    "䝉": "蒙",
    "䕶": "护",
    "㓂": "寇",
    "㕘": "参",
    "𥳑": "简",
    "𫉬": "获",
    # 日新字体
    "増": "增",
    "乗": "乘",
    "従": "从",
    "毎": "每",
    "収": "收",
    "両": "两",
    "児": "儿",
    "焼": "烧",
    "抜": "拔",
    "挿": "插",
    "説": "说",
    "録": "录",
    "舎": "舍",
    "暦": "历",
    "覧": "览",
    "郷": "乡",
    "総": "总",
    # 旧字形 / 四库常见
    "爲": "为",
    "涙": "泪",
    "尙": "尚",
    "巻": "卷",
    "寳": "宝",
    "頬": "颊",
    "圗": "图",
    "覇": "霸",
    "帶": "带",
    "帯": "带",
    "眞": "真",
    "煕": "熙",
    "熈": "熙",  # 用户点名
    "餘": "余",
    "馀": "余",
    "逹": "达",
    "邉": "边",
    "衆": "众",
    "萬": "万",
    "歲": "岁",
    "歳": "岁",
    "亞": "亚",
    "髙": "高",  # 用户点名
    "宻": "密",  # 用户点名
    "畱": "留",  # 用户点名
    "戸": "户",  # 用户点名
    "徳": "德",
    "竒": "奇",
    "竝": "并",
    "敎": "教",
    "峯": "峰",
    "徧": "遍",
    "衞": "卫",
    "黒": "黑",
    "逺": "远",
    "隂": "阴",
    "闗": "关",
    "郞": "郎",
    "飮": "饮",
    "旣": "既",
    "冝": "宜",
    "敍": "叙",
    "擧": "举",
    "槪": "概",
    "奬": "奖",
    "綫": "线",
    "羣": "群",
    "綉": "绣",
    "舘": "馆",
    "硏": "研",
}


def normalize(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for a, b in MULTI.items():
        n = text.count(a)
        if n:
            text = text.replace(a, b)
            counts[f"{a}→{b}"] = n
    for a, b in VARIANT_MAP.items():
        n = text.count(a)
        if n:
            text = text.replace(a, b)
            counts[f"{a}→{b}"] = n
    return text, counts


def iter_active(files: list[str] | None):
    if files:
        for f in files:
            yield Path(f)
        return
    for p in sorted(DATA.rglob("*.txt")):
        if any(part.startswith("_") for part in p.relative_to(DATA).parts):
            continue
        yield p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total_files = 0
    changed_files = 0
    grand: dict[str, int] = {}

    for path in iter_active(args.files or None):
        if not path.exists():
            print("MISS", path)
            continue
        total_files += 1
        raw = path.read_text(encoding="utf-8", errors="replace")
        fixed, counts = normalize(raw)
        if not counts:
            continue
        changed_files += 1
        for k, v in counts.items():
            grand[k] = grand.get(k, 0) + v
        print(f"{path.relative_to(DATA) if DATA in path.parents else path}: {counts}")
        if not args.dry_run:
            path.write_text(fixed, encoding="utf-8")

    print("---")
    print(f"scanned={total_files} changed={changed_files}")
    # highlight user keys
    for k in ["宻→密", "髙→高", "畱→留", "戸→户", "熈→熙", "煕→熙", "徳→德", "隂→阴", "闗→关"]:
        if k in grand:
            print("USER", k, grand[k])
    top = sorted(grand.items(), key=lambda x: -x[1])[:25]
    print("top:", top)

    # residual assert on key forms in active
    if not args.dry_run:
        residual = {k: 0 for k in ["宻", "髙", "畱", "戸", "熈", "煕"]}
        for path in iter_active(args.files or None):
            t = path.read_text(encoding="utf-8", errors="replace")
            for k in residual:
                residual[k] += t.count(k)
        print("residual key", residual)
        bad = {k: v for k, v in residual.items() if v}
        if bad:
            print("WARN residual remains", bad)
            sys.exit(1)
        print("OK residual key forms = 0")


if __name__ == "__main__":
    main()
