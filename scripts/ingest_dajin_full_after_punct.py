#!/usr/bin/env python3
"""Watch full 《大金国志》 auto-punct job, then t2s + variant + chrono resegment → active.

Input: /tmp/大金国志_to_punct.txt (punct job in-place rewrite)
Raw full unpunct backup stays at data/_raw_no_punct/大金国志.txt
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/root/projects/text-search")
sys.path.insert(0, str(ROOT / "scripts"))

from opencc import OpenCC  # noqa: E402
from resegment_annots import resegment  # noqa: E402

PUNCT_PATH = Path("/tmp/大金国志_to_punct.txt")
PUNCT_LOG = Path("/tmp/dajin_punct.log")
RAW_KEEP = ROOT / "data" / "_raw_no_punct" / "大金国志.txt"
ACTIVE = ROOT / "data" / "辽宋夏金" / "大金国志.txt"
META_PATH = ROOT / "data" / "books_meta.json"
LOG = ROOT / "logs" / "dajin_full_ingest.log"
WATCH_PID = int(sys.argv[1]) if len(sys.argv) > 1 else None

# plain chars of full raw (gate)
MIN_PLAIN = 140_000
MIN_CHARS = 160_000  # punctuated full book should grow past raw plain
MIN_PUNCT = 8_000

# extension / old-form map (subset + known 大金国志 forms)
VARIANT = {
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
    "乗": "乘",
    "従": "从",
    "毎": "每",
    "収": "收",
    "両": "两",
    "覧": "览",
    "郷": "乡",
    "総": "总",
    "児": "儿",
    "焼": "烧",
    "抜": "拔",
    "挿": "插",
    "説": "说",
    "録": "录",
    "舎": "舍",
    "暦": "历",
    "爲": "为",
    "涙": "泪",
    "尙": "尚",
    "巻": "卷",
    "寳": "宝",
    "頬": "颊",
    "圗": "图",
    "覇": "霸",
    "帶": "带",
    "眞": "真",
    "煕": "熙",
    "餘": "余",
    "馀": "余",
    "逹": "达",
    "邉": "边",
    "來": "来",
    "時": "时",
    "國": "国",
    "與": "与",
    "無": "无",
    "於": "于",
    "對": "对",
    "後": "后",
    "爲": "为",
    "衆": "众",
    "萬": "万",
    "歲": "岁",
    "歳": "岁",
    "亞": "亚",
    # 用户点名 + 四库旧形
    "髙": "高",
    "宻": "密",
    "畱": "留",
    "戸": "户",
    "徳": "德",
    "隂": "阴",
    "闗": "关",
    "竒": "奇",
    "徧": "遍",
    "衞": "卫",
    "黒": "黑",
    "逺": "远",
    "増": "增",
    "帯": "带",
    "帶": "带",
}


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def apply_variant(t: str) -> str:
    for a, b in VARIANT.items():
        t = t.replace(a, b)
    return t


def light_clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # strip wiki/四库 chrome crumbs if any
    drop = (
        r"^返回顶部$",
        r"^Public domain.*$",
        r"^\[编辑\]$",
        r"^<史部.*>$",
    )
    lines = []
    blank = 0
    for ln in text.split("\n"):
        s = ln.rstrip().replace("\u3000", "").strip()
        if not s:
            blank += 1
            if blank <= 1:
                lines.append("")
            continue
        if any(re.match(p, s) for p in drop):
            continue
        blank = 0
        lines.append(s)
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    if WATCH_PID:
        log(f"watch pid={WATCH_PID} path={PUNCT_PATH}")
        while alive(WATCH_PID):
            if PUNCT_LOG.exists():
                tail = [l for l in PUNCT_LOG.read_text(errors="replace").splitlines() if "%" in l or "done" in l]
                if tail:
                    log("punct: " + tail[-1].strip())
            time.sleep(30)
        log("punct process exited")
    else:
        log("no pid; assume punct file already final")

    if not PUNCT_PATH.exists():
        log(f"MISSING {PUNCT_PATH}")
        return 1

    t = PUNCT_PATH.read_text(encoding="utf-8", errors="replace")
    punct0 = len(re.findall(r"[，。！？；：、]", t))
    plain = re.sub(r"[，。！？；：、\"“”‘’＇\s]", "", t)
    # drop auto header for plain estimate of body
    plain_body = re.sub(r"（本文件[^）]*）", "", plain)
    log(f"punct file chars={len(t)} plain≈{len(plain_body)} punct={punct0}")

    if len(plain_body) < MIN_PLAIN:
        log(f"ABORT too short plain={len(plain_body)} < {MIN_PLAIN} (likely incomplete)")
        return 2
    if punct0 < MIN_PUNCT:
        log(f"ABORT low punct={punct0}")
        return 3

    cc = OpenCC("t2s")
    t = cc.convert(t)
    t = apply_variant(t)
    t = light_clean(t)

    # chrono resegment
    out = resegment(t, style="chrono")
    # ensure header note kept
    if not out.lstrip().startswith("（本文件"):
        head = "（本文件由模型自动标点：raynardj/classical-chinese-punctuation-guwen-biaodian；全本重跑；请以原典复核）\n\n"
        out = head + out
    if not out.endswith("\n"):
        out += "\n"

    punct = len(re.findall(r"[，。！？；：、]", out))
    paras = [p for p in out.split("\n\n") if p.strip()]
    bad_starts = sum(1 for p in paras if p and p[0] in "【】〈〉")
    vols = set(re.findall(r"大金国志卷([首一二三四五六七八九十百零〇两\d]+)", out))
    vols |= set(re.findall(r"钦定重订大金国志卷([首一二三四五六七八九十百零〇两\d]+)", out))

    log(
        f"reseg paras={len(paras)} chars={len(out)} punct={punct} "
        f"bad_starts={bad_starts} vol_markers={len(vols)}"
    )
    if len(out) < MIN_CHARS and len(plain_body) < MIN_PLAIN:
        log("ABORT after reseg still short")
        return 4

    # backup incomplete active if any
    if ACTIVE.exists():
        bak = ACTIVE.with_suffix(ACTIVE.suffix + f".bak_before_full_{time.strftime('%Y%m%d_%H%M%S')}")
        ACTIVE.rename(bak)
        log(f"backup old active -> {bak.name}")

    ACTIVE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(out, encoding="utf-8")

    # also keep a full punct intermediate under _raw (not overwriting unpunct raw)
    inter = ROOT / "data" / "_raw_no_punct" / "大金国志_full_punct.txt"
    inter.write_text(out, encoding="utf-8")

    # never clobber full unpunct raw
    if RAW_KEEP.exists():
        rpunct = len(re.findall(r"[，。！？；：、]", RAW_KEEP.read_text(encoding="utf-8", errors="replace")))
        log(f"raw keep intact punct_marks={rpunct} size={RAW_KEEP.stat().st_size}")

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["大金国志"] = {"era": "南宋", "author": "宇文懋昭（题）"}
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log(
        f"INGEST OK -> {ACTIVE} bytes={ACTIVE.stat().st_size} "
        f"chars={len(out)} paras={len(paras)} punct={punct}"
    )
    # smoke
    for kw in ("乌珠", "天会", "宗弼", "许亢宗"):
        hits = sum(1 for p in paras if kw in p)
        log(f"  smoke {kw}: {hits}")
    log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
