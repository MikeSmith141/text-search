#!/usr/bin/env python3
"""等当前 auto_punctuate 结束后，给辽宋夏金 raw 无标点书排队标点并入库。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]

WATCH_PID = int(sys.argv[1]) if len(sys.argv) > 1 else 3418750
ROOT = ROOT
RAW = ROOT / "data" / "_raw_no_punct"
ACTIVE = ROOT / "data" / "辽宋夏金"
META_PATH = ROOT / "data" / "books_meta.json"
LOG = ROOT / "logs" / "liaosong_punct_queue.log"
BOOKS = [
    ("大金国志.txt", "大金国志", "南宋", "宇文懋昭（题）"),
    ("东都事略.txt", "东都事略", "南宋", "王称"),
    ("宋史纪事本末.txt", "宋史纪事本末", "明", "陈邦瞻"),
]
MIN_PUNCT = 80
cc = OpenCC("t2s")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    log(f"queue start; watch pid={WATCH_PID} alive={alive(WATCH_PID)}")
    while alive(WATCH_PID):
        # optional progress from yishi log
        ap = ROOT / "logs" / "auto_punctuate.log"
        if ap.exists():
            lines = [l for l in ap.read_text(errors="replace").splitlines() if "绎史" in l]
            if lines:
                log("upstream: " + lines[-1].strip())
        time.sleep(60)
    log("upstream punct process ended")

    paths = []
    for fname, *_ in BOOKS:
        p = RAW / fname
        if p.exists():
            paths.append(str(p))
            log(f"queue file {p} size={p.stat().st_size}")
        else:
            log(f"MISSING raw {p}")
    if not paths:
        log("no paths; exit")
        return

    cmd = [
        "python3",
        "-u",
        str(ROOT / "scripts" / "auto_punctuate.py"),
        *paths,
        "--win",
        "240",
    ]
    log("run: " + " ".join(cmd))
    with (ROOT / "logs" / "liaosong_auto_punctuate.log").open("a", encoding="utf-8") as out:
        rc = subprocess.call(cmd, cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT)
    log(f"auto_punctuate exit={rc}")

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for fname, name, era, author in BOOKS:
        src = RAW / fname
        if not src.exists():
            log(f"skip missing {fname}")
            continue
        t = cc.convert(src.read_text(encoding="utf-8", errors="replace"))
        # light variants
        for a, b in (("馀", "余"), ("巻", "卷"), ("録", "录"), ("眞", "真")):
            t = t.replace(a, b)
        punct = len(re.findall(r"[，。！？；：、]", t))
        # always write back simplified raw
        src.write_text(t, encoding="utf-8")
        meta[name] = {"era": era, "author": author}
        if punct < MIN_PUNCT:
            log(f"LOW punct {name} punct={punct}; keep raw only")
            continue
        dest = ACTIVE / f"{name}.txt"
        dest.write_text(t, encoding="utf-8")
        log(f"INGEST {name} chars={len(t)} punct={punct} -> {dest}")
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log("DONE queue")


if __name__ == "__main__":
    main()
