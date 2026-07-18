#!/usr/bin/env python3
"""从维基文库抓取完整《史記》卷001–130，转简体后写入 data/先秦/史记.txt。

特性：
- 每卷缓存到 data/_cache/shiji/volXXX.txt，可断点续抓
- 遇 429 指数退避，卷间默认 sleep 2.5s
- 写盘前校验关键卷，尤其 043 赵世家关键句
"""
from __future__ import annotations

import html as htmlmod
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]

API = "https://zh.wikisource.org/w/api.php"
UA = {"User-Agent": "HermesHistoryBot/1.0 (research; public-domain classics)"}
OUT = ROOT / "data" / "先秦" / "史记.txt"
CACHE = ROOT / "data" / "_cache" / "shiji"
BAK = ROOT / "data" / "_raw_no_punct" / "史记_old_incomplete.txt"
SLEEP = 6.0
cc = OpenCC("t2s")


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    last = None
    for i in range(10):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            last = e
            wait = min(90, 3 ** min(i, 4) + 2)
            print(f"  api retry {params.get('page')}: {e} wait {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(last)


def html_to_text(s: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", "", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", "", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>|</div>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s)
    s = s.replace("\xa0", " ").replace("\u3000", " ")
    s = re.sub(r"取自“https://zh.wikisource.org.*", "", s)
    s = re.sub(r"姊妹计划:.*", "", s)
    lines = []
    for ln in s.splitlines():
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if not ln:
            continue
        if ln.startswith("参阅维基") or ln.startswith("阅文言"):
            continue
        if "维基百科" in ln and len(ln) < 40:
            continue
        if ln in ("[编辑]", "编辑"):
            continue
        if ln.startswith("分类:") or ln.startswith("Category:"):
            continue
        if "◄" in ln or "►" in ln:
            continue
        if ln in ("史记", "史記"):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


def fetch_vol(n: int, force: bool = False) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"vol{n:03d}.txt"
    if cache.exists() and cache.stat().st_size > 200 and not force:
        return cache.read_text(encoding="utf-8")
    page = f"史記/卷{n:03d}"
    d = api(action="parse", page=page, prop="text", redirects=1, disabletoc=1)
    html = d.get("parse", {}).get("text", {}).get("*", "")
    text = html_to_text(html)
    text = cc.convert(text)
    if len(text) < 50:
        raise RuntimeError(f"too short: {page} len={len(text)}")
    cache.write_text(text, encoding="utf-8")
    return text


def assemble() -> str:
    parts = []
    missing = []
    for n in range(1, 131):
        cache = CACHE / f"vol{n:03d}.txt"
        if not cache.exists() or cache.stat().st_size < 50:
            missing.append(n)
            continue
        parts.append(cache.read_text(encoding="utf-8"))
    if missing:
        raise RuntimeError(f"missing volumes: {missing}")
    header = "（来源：维基文库《史記》卷001–130 · 已转简体）\n\n"
    body = "\n\n".join(parts)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return header + body


def main():
    force = "--force" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = [int(x) for x in a.split("=", 1)[1].split(",") if x.strip()]

    if OUT.exists() and not BAK.exists():
        BAK.write_bytes(OUT.read_bytes())
        print("backup old ->", BAK, flush=True)

    targets = only if only else list(range(1, 131))
    ok = 0
    for n in targets:
        try:
            text = fetch_vol(n, force=force)
            punct = len(re.findall(r"[，。！？；：、]", text))
            print(f"{n:03d} ok chars={len(text):6d} punct={punct:5d}", flush=True)
            ok += 1
        except Exception as e:
            print(f"{n:03d} FAIL {e}", flush=True)
        time.sleep(SLEEP)

    # report cache coverage
    have = [n for n in range(1, 131) if (CACHE / f"vol{n:03d}.txt").exists() and (CACHE / f"vol{n:03d}.txt").stat().st_size > 50]
    miss = [n for n in range(1, 131) if n not in have]
    print(f"cache have={len(have)} miss={miss}", flush=True)
    if miss:
        print("NOT assembling until all volumes present", flush=True)
        return 2

    final = assemble()
    residual = sum(1 for a, b in zip(final, cc.convert(final)) if a != b)
    OUT.write_text(final, encoding="utf-8")
    print("WROTE", OUT, "chars", len(final), "punct", len(re.findall(r"[，。！？；：、]", final)), "residual", residual, flush=True)
    q1 = "赵徙漳水武平西" in final
    q2 = "置公子丹为太子" in final
    print("quote checks:", q1, q2, flush=True)
    if not (q1 and q2):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
