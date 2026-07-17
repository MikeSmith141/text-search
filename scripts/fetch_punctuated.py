#!/usr/bin/env python3
"""从维基文库抓取有标点古籍，替换本地无标点版本。"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://zh.wikisource.org/w/api.php"
UA = {"User-Agent": "HermesHistoryBot/1.0 (research; public-domain classics)"}
OUT = Path("/root/projects/text-search/data/先秦")

# 目标书 -> 维基文库抓取策略
JOBS = {
    "鬻子": {"mode": "pages", "pages": ["鬻子"]},
    "鹖冠子": {"mode": "pages", "pages": ["鶡冠子"]},
    "金楼子": {"mode": "prefix", "prefix": "金樓子/"},
    "穆天子传": {"mode": "prefix", "prefix": "穆天子傳/"},
    "考工记": {"mode": "pages", "pages": ["周禮/冬官考工記"]},
    "路史": {"mode": "prefix", "prefix": "路史/"},
    "绎史": {"mode": "prefix_or_siku", "prefix": "繹史/", "fallback_prefix": "繹史 (四庫全書本)/"},
    "七国考": {"mode": "prefix", "prefix": "七國攷 (四庫全書本)/", "fallback_pages": ["七國攷 (四庫全書本)"]},
}


def api(**params):
    params.setdefault("format", "json")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    for i in range(7):
        try:
            with urllib.request.urlopen(req, timeout=50) as r:
                return json.load(r)
        except Exception as e:
            wait = 2 ** i + 1
            print(f"  api retry {params.get('page') or params.get('apprefix')}: {e} wait {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"api failed: {params}")


def html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html)
    text = re.sub(r"<style[\s\S]*?</style>", "", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>|</div>|</li>|</h\d>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    for a, b in [("&nbsp;", " "), ("&#160;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">")]:
        text = text.replace(a, b)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = re.sub(r"取自“https://zh.wikisource.org.*", "", text)
    # 去掉维基模板噪音
    text = re.sub(r"姊妹计划:.*", "", text)
    return text.strip()


def get_page_text(title: str) -> str:
    d = api(action="parse", page=title, prop="text", redirects=1, disabletoc=1)
    html = d.get("parse", {}).get("text", {}).get("*", "")
    return html_to_text(html)


def list_prefix(prefix: str):
    cont = None
    titles = []
    while True:
        kw = dict(action="query", list="allpages", apprefix=prefix, aplimit=100)
        if cont:
            kw["apcontinue"] = cont
        d = api(**kw)
        titles += [x["title"] for x in d.get("query", {}).get("allpages", [])]
        cont = d.get("continue", {}).get("apcontinue")
        if not cont:
            break
    return titles


def punct_count(s: str) -> int:
    return len(re.findall(r"[，。！？；：、]", s))


def natural_key(title: str):
    m = re.search(r"(\d+)$", title)
    if m:
        return (0, int(m.group(1)), title)
    # 卷一 卷上
    m = re.search(r"卷([一二三四五六七八九十百零〇]+|[上下])", title)
    if not m:
        return (1, 999, title)
    s = m.group(1)
    if s in ("上",):
        return (0, 1, title)
    if s in ("下",):
        return (0, 2, title)
    mp = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if s == "十":
        return (0, 10, title)
    if s.startswith("十"):
        return (0, 10 + mp.get(s[1], 0), title)
    if "十" in s:
        a, b = s.split("十", 1)
        return (0, mp.get(a, 1) * 10 + (mp.get(b, 0) if b else 0), title)
    return (0, mp.get(s, 999), title)


def fetch_job(name: str, conf: dict):
    print(f"\n=== {name} ===", flush=True)
    titles = []
    mode = conf["mode"]
    if mode == "pages":
        titles = conf["pages"]
    elif mode == "prefix":
        titles = list_prefix(conf["prefix"])
        if not titles and conf.get("fallback_pages"):
            titles = conf["fallback_pages"]
    elif mode == "prefix_or_siku":
        titles = list_prefix(conf["prefix"])
        if not titles:
            titles = list_prefix(conf["fallback_prefix"])
    titles = sorted(set(titles), key=natural_key)
    print(" pages:", len(titles), titles[:8], ("..." if len(titles) > 8 else ""), flush=True)
    if not titles:
        return False, "no pages"

    parts = [f"（来源：维基文库，有标点公版）\n"]
    total_punct = 0
    ok = 0
    for i, t in enumerate(titles, 1):
        try:
            text = get_page_text(t)
        except Exception as e:
            print(f"  FAIL {t}: {e}", flush=True)
            time.sleep(2)
            continue
        p = punct_count(text)
        total_punct += p
        parts.append(f"【{t}】\n{text}")
        ok += 1
        print(f"  {i}/{len(titles)} {t} chars={len(text)} punct={p}", flush=True)
        time.sleep(1.4)

    if ok == 0:
        return False, "all pages failed"
    body = "\n\n".join(parts) + "\n"
    # 考工记 单独文件名
    out_name = "考工记.txt" if name == "考工记" else f"{name}.txt"
    out = OUT / out_name
    # 如果原来有 考工记解 且本次是考工记，另存
    out.write_text(body, encoding="utf-8")
    print(f"  written {out} chars={len(body)} punct={total_punct} pages={ok}", flush=True)
    return True, f"punct={total_punct} pages={ok}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, conf in JOBS.items():
        try:
            ok, msg = fetch_job(name, conf)
            results[name] = ("OK" if ok else "FAIL", msg)
        except Exception as e:
            results[name] = ("FAIL", str(e))
        time.sleep(2)
    print("\n==== SUMMARY ====")
    for k, (s, m) in results.items():
        print(f"{s} {k}: {m}")


if __name__ == "__main__":
    main()
