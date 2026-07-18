#!/usr/bin/env python3
"""补缺先秦诸子/兵书/医书/楚辞：从 daizhige 公版源下载，转简体、轻清洗、写 meta。"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]

REPO = "https://raw.githubusercontent.com/garychowcmu/daizhigev20/master"
UA = {"User-Agent": "HermesHistoryBot/1.0 (research; public-domain classics)"}
OUT = ROOT / "data" / "先秦"
RAW = ROOT / "data" / "_raw_no_punct"
META_PATH = ROOT / "data" / "books_meta.json"
cc = OpenCC("t2s")

# name -> (rel_path or list of rel_paths to concat, era, author, note)
# 有标点优先；无标点的会落到 raw 并标记 need_punct
JOBS = {
    "管子": {
        "paths": ["子藏/法家/管子.txt"],
        "era": "春秋",
        "author": "管仲（托名）",
        "need_punct": True,  # 四库白文
    },
    "孙子兵法": {
        "paths": ["子藏/兵家/孙子兵法.txt"],
        "era": "春秋",
        "author": "孙武",
    },
    "司马法": {
        "paths": ["子藏/兵家/司马法.txt"],
        "era": "战国",
        "author": "司马穰苴（托名）",
        "need_punct": True,
    },
    "孙膑兵法": {
        "paths": ["子藏/兵家/孙膑兵法.txt"],
        "era": "战国",
        "author": "孙膑",
    },
    "太公兵法": {
        "paths": ["子藏/兵家/太公兵法.txt"],
        "era": "西周",
        "author": "姜尚（辑佚）",
    },
    "六韬": {
        "paths": ["子藏/兵家/六韬.txt"],
        "era": "战国",
        "author": "姜尚（托名）",
    },
    "吴子兵法": {
        "paths": ["子藏/兵家/吴子兵法.txt"],
        "era": "战国",
        "author": "吴起",
    },
    "尉缭子": {
        "paths": ["子藏/兵家/尉缭子.txt"],
        "era": "战国",
        "author": "尉缭",
    },
    "老子": {
        "paths": ["道藏/正统道藏洞神部/本文类/道德真经.txt"],
        "era": "春秋",
        "author": "老聃",
    },
    "道德经": {
        "paths": ["道藏/正统道藏洞神部/本文类/道德真经.txt"],
        "era": "春秋",
        "author": "老聃",
        "alias_of": "老子",
    },
    "庄子": {
        "paths": ["道藏/藏外/庄子.txt"],
        "era": "战国",
        "author": "庄周",
    },
    "关尹子": {
        "paths": ["道藏/藏外/关尹子.txt"],
        "era": "战国",
        "author": "关尹喜（托名）",
    },
    "列子": {
        "paths": ["道藏/藏外/列子.txt"],
        "era": "战国",
        "author": "列御寇（托名）",
    },
    "素问": {
        "paths": ["医藏/黄帝内经素问.txt"],
        "era": "战国至汉",
        "author": "佚名（王冰次注）",
    },
    "黄帝内经": {
        # 素问 + 灵枢 合编
        "paths": ["医藏/黄帝内经素问.txt", "医藏/黄帝内经灵枢.txt"],
        "era": "战国至汉",
        "author": "佚名",
        "join_titles": ["黄帝内经素问", "黄帝内经灵枢"],
    },
    "抱朴子": {
        "paths": ["道藏/藏外/抱朴子内篇.txt", "道藏/藏外/抱朴子外篇.txt"],
        "era": "东晋",
        "author": "葛洪",
        "join_titles": ["抱朴子内篇", "抱朴子外篇"],
    },
    "文子": {
        "paths": ["道藏/藏外/文子.txt"],
        "era": "战国",
        "author": "辛钘（托名）",
        "need_punct": True,
    },
    "商君书": {
        "paths": ["子藏/法家/商子.txt"],
        "era": "战国",
        "author": "商鞅",
    },
    "邓析子": {
        "paths": ["子藏/法家/邓析子.txt"],
        "era": "春秋",
        "author": "邓析",
    },
    "申子": {
        "paths": ["子藏/诸子/申子.txt"],
        "era": "战国",
        "author": "申不害（辑佚）",
    },
    "慎子": {
        "paths": ["子藏/诸子/慎子.txt"],
        "era": "战国",
        "author": "慎到",
    },
    "公孙龙子": {
        "paths": ["子藏/诸子/公孙龙子.txt"],
        "era": "战国",
        "author": "公孙龙",
        "need_punct": True,
    },
    "鬼谷子": {
        "paths": ["子藏/诸子/鬼谷子.txt"],
        "era": "战国",
        "author": "鬼谷子（托名）",
    },
    "楚辞": {
        "paths": ["诗藏/楚辞/楚辞.txt"],
        "era": "战国",
        "author": "屈原等",
    },
}


def fetch(rel: str) -> str:
    url = REPO + "/" + urllib.parse.quote(rel)
    req = urllib.request.Request(url, headers=UA)
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            break
        except Exception as e:
            wait = 2 ** i
            print(f"  retry {rel}: {e} wait {wait}s", flush=True)
            time.sleep(wait)
    else:
        raise RuntimeError(f"download failed: {rel}")
    for enc in ("utf-8", "gb18030", "utf-8-sig"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def light_clean(text: str) -> str:
    text = text.replace("\ufeff", "")
    # wiki/license leftovers if any
    text = re.sub(r"\[编辑\]", "", text)
    text = re.sub(r"此作品在全世界都属于公有领域[^\n]*\n?", "", text)
    text = re.sub(r"Public domain[^\n]*\n?", "", text, flags=re.I)
    text = re.sub(r"↑返回顶部\n?", "", text)
    lines = []
    blank = 0
    for ln in text.splitlines():
        s = ln.rstrip()
        st = s.strip()
        if st in {"Public domain", "false", "falsefalse", "目录", "目　录"}:
            continue
        if re.fullmatch(r"Public\s*domain.*", st or "", re.I):
            continue
        if not st:
            blank += 1
            if blank <= 2:
                lines.append("")
            continue
        blank = 0
        lines.append(s)
    while lines and not lines[-1].strip():
        lines.pop()
    text = "\n".join(lines).strip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def punct_count(t: str) -> int:
    return len(re.findall(r"[，。！？；：、]", t))


def process_job(name: str, conf: dict) -> dict:
    print(f"\n=== {name} ===", flush=True)
    chunks = []
    for i, rel in enumerate(conf["paths"]):
        raw = fetch(rel)
        raw = cc.convert(raw)
        raw = light_clean(raw)
        titles = conf.get("join_titles") or []
        if titles and i < len(titles):
            chunks.append(f"【{titles[i]}】\n{raw.strip()}\n")
        else:
            chunks.append(raw.strip() + "\n")
        print(f"  got {rel}: chars={len(raw)} punct={punct_count(raw)}", flush=True)
        time.sleep(0.3)

    body = "\n".join(chunks).strip() + "\n"
    # source banner
    srcs = " + ".join(conf["paths"])
    header = f"（来源：daizhigev20 · {srcs} · 已转简体）\n\n"
    text = header + body
    pc = punct_count(text)
    ratio = pc / max(len(text), 1)
    need = conf.get("need_punct") or pc < 80

    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    if need:
        # 先存 raw，不进索引（或进索引但标警告——按铁律：无标点不进检索库）
        raw_path = RAW / f"{name}.txt"
        raw_path.write_text(text, encoding="utf-8")
        print(f"  NEED_PUNCT -> {raw_path} chars={len(text)} punct={pc}", flush=True)
        return {
            "name": name,
            "status": "need_punct",
            "chars": len(text),
            "punct": pc,
            "ratio": round(ratio, 4),
            "path": str(raw_path),
        }

    out = OUT / f"{name}.txt"
    out.write_text(text, encoding="utf-8")
    print(f"  OK -> {out} chars={len(text)} punct={pc} ratio={ratio:.4f}", flush=True)
    return {
        "name": name,
        "status": "ok",
        "chars": len(text),
        "punct": pc,
        "ratio": round(ratio, 4),
        "path": str(out),
        "era": conf.get("era", ""),
        "author": conf.get("author", ""),
    }


def update_meta(results: list[dict]):
    meta = {}
    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    for r in results:
        if r.get("status") != "ok":
            continue
        name = r["name"]
        conf = JOBS[name]
        meta[name] = {
            "era": conf.get("era", ""),
            "author": conf.get("author", ""),
        }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"meta updated -> {META_PATH} total keys={len(meta)}", flush=True)


def main():
    results = []
    for name, conf in JOBS.items():
        try:
            results.append(process_job(name, conf))
        except Exception as e:
            print(f"  FAIL {name}: {e}", flush=True)
            results.append({"name": name, "status": "fail", "error": str(e)})
        time.sleep(0.4)

    update_meta(results)
    print("\n==== SUMMARY ====")
    ok = [r for r in results if r.get("status") == "ok"]
    np = [r for r in results if r.get("status") == "need_punct"]
    fail = [r for r in results if r.get("status") == "fail"]
    for r in results:
        print(
            f"{r.get('status', '?'):12} {r['name']}: chars={r.get('chars')} punct={r.get('punct')} {r.get('error','')}"
        )
    print(f"\nOK={len(ok)} NEED_PUNCT={len(np)} FAIL={len(fail)}")
    if np:
        print("pending punct:", [r["name"] for r in np])


if __name__ == "__main__":
    main()
