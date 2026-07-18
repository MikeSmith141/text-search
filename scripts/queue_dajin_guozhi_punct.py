#!/usr/bin/env python3
"""等上游 auto_punctuate 结束后，只给《大金国志》自动标点→简体→入库辽宋夏金。
不处理东都事略 / 宋史纪事本末 / 辽史纪事本末。
"""
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
RAW = ROOT / "data" / "_raw_no_punct" / "大金国志.txt"
ACTIVE = ROOT / "data" / "辽宋夏金" / "大金国志.txt"
META_PATH = ROOT / "data" / "books_meta.json"
LOG = ROOT / "logs" / "dajin_guozhi_punct.log"
PUNCT_LOG = ROOT / "logs" / "dajin_auto_punctuate.log"
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


def light_clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines, blank = [], 0
    for ln in text.split("\n"):
        s = ln.rstrip().replace("\u3000", "").strip()
        if not s:
            blank += 1
            if blank <= 1:
                lines.append("")
            continue
        blank = 0
        lines.append(s)
    text = "\n".join(lines).strip() + "\n"
    for a, b in (("馀", "余"), ("巻", "卷"), ("録", "录"), ("眞", "真"), ("煕", "熙")):
        text = text.replace(a, b)
    return text


def main() -> None:
    if not RAW.exists():
        log(f"MISSING {RAW}")
        return
    log(f"queue start; only 大金国志; watch pid={WATCH_PID} alive={alive(WATCH_PID)}")
    while alive(WATCH_PID):
        ap = ROOT / "logs" / "auto_punctuate.log"
        if ap.exists():
            lines = [l for l in ap.read_text(errors="replace").splitlines() if "绎史" in l]
            if lines:
                log("upstream: " + lines[-1].strip())
        time.sleep(60)
    log("upstream punct process ended; start 大金国志")

    cmd = [
        "python3",
        "-u",
        str(ROOT / "scripts" / "auto_punctuate.py"),
        str(RAW),
        "--win",
        "240",
        "--force",
    ]
    log("run: " + " ".join(cmd))
    with PUNCT_LOG.open("a", encoding="utf-8") as out:
        rc = subprocess.call(cmd, cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT)
    log(f"auto_punctuate exit={rc}")

    t = RAW.read_text(encoding="utf-8", errors="replace")
    t = cc.convert(t)
    t = light_clean(t)
    punct = len(re.findall(r"[，。！？；：、]", t))
    RAW.write_text(t, encoding="utf-8")  # keep simplified punct raw too
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    meta["大金国志"] = {"era": "南宋", "author": "宇文懋昭（题）"}
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if punct < MIN_PUNCT:
        log(f"LOW punct={punct}; keep raw only, NOT ingest active")
        return

    ACTIVE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(t, encoding="utf-8")
    log(f"INGEST 大金国志 chars={len(t)} punct={punct} dens={punct/max(len(t),1):.4f} -> {ACTIVE}")
    log("DONE")


if __name__ == "__main__":
    main()
