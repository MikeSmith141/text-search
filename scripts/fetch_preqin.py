#!/usr/bin/env python3
from pathlib import Path
"""从殆知阁 daizhigev20 下载先秦相关公版古籍到 data/先秦/"""
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = str(ROOT / "data" / "先秦")
REPO = "https://raw.githubusercontent.com/garychowcmu/daizhigev20/master"
UA = "Mozilla/5.0 (compatible; HermesHistoryBot/1.0; research)"

# 书名 -> 仓库相对路径
BOOKS = {
    "春秋左传": "儒藏/春秋/春秋左传.txt",
    "春秋公羊传": "儒藏/春秋/春秋公羊传.txt",
    "春秋谷梁传": "儒藏/春秋/春秋谷梁传.txt",
    "史记": "史藏/正史/史记.txt",
    "国语": "史藏/别史/国语.txt",
    "尚书": "儒藏/尚书/尚书.txt",
    "逸周书": "史藏/别史/逸周书.txt",
    "战国纵横家书": "子藏/诸子/马王堆帛书战国纵横家书.txt",
    "韩非子": "子藏/诸子/韩非子.txt",
    "韩诗外传": "儒藏/诗经/韩诗外传.txt",
    "鹖冠子": "子藏/诸子/鹖冠子.txt",
    "淮南子": "子藏/诸子/淮南子.txt",
    "金楼子": "子藏/诸子/金楼子.txt",
    "考工记解": "儒藏/礼经/考工记解.txt",
    "孔子家语": "儒藏/语录/孔子家语.txt",
    "论语": "儒藏/四书/论语.txt",
    "孟子": "儒藏/四书/孟子.txt",
    "荀子": "子藏/诸子/荀子.txt",
    "古列女传": "史藏/传记/古列女传.txt",
    "列女传": "史藏/传记/列女传.txt",
    "路史": "史藏/别史/路史.txt",
    "吕氏春秋": "子藏/诸子/吕氏春秋.txt",
    "墨子": "子藏/诸子/墨子.txt",
    "穆天子传": "子藏/笔记/穆天子传.txt",
    "七国考": "史藏/政书/七国考.txt",
    "礼记": "儒藏/礼经/礼记.txt",
    "周礼": "儒藏/礼经/周礼.txt",
    "仪礼": "儒藏/礼经/仪礼.txt",
    "诗经": "儒藏/诗经/诗经.txt",
    "说苑": "儒藏/语录/说苑.txt",
    "吴越春秋": "史藏/载记/吴越春秋.txt",
    "新书": "儒藏/语录/新书.txt",
    "新序": "儒藏/语录/新序.txt",
    "晏子春秋": "史藏/传记/晏子春秋.txt",
    "鬻子": "子藏/诸子/鬻子.txt",
    "越绝书": "史藏/载记/越绝书.txt",
    "竹书纪年": "史藏/编年/竹书纪年.txt",
    "子华子": "子藏/诸子/子华子.txt",
    "资治通鉴": "史藏/编年/资治通鉴.txt",
    "郁离子": "子藏/诸子/郁离子.txt",
    "绎史": "史藏/纪事本末/绎史.txt",
    "夜航船": "子藏/类书/夜航船.txt",
    "太平御览": "子藏/类书/太平御览.txt",
    "水经注": "史藏/地理/水经注.txt",
}


def download(name: str, rel: str) -> tuple[str, str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{name}.txt")
    if os.path.isfile(out) and os.path.getsize(out) > 1000:
        return "skip", f"已存在 {os.path.getsize(out)} bytes"
    url = REPO + "/" + urllib.parse.quote(rel)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception as e:
        return "fail", str(e)
    # 轻清洗：去掉过多空行
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = data.decode("gb18030", errors="replace")
    lines = [ln.rstrip() for ln in text.splitlines()]
    # 保留空行但压缩连续空行
    cleaned = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(ln)
    content = "\n".join(cleaned).strip() + "\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    return "ok", f"{len(content)} chars -> {out}"


def main():
    ok = fail = skip = 0
    for name, rel in BOOKS.items():
        status, msg = download(name, rel)
        print(f"[{status}] {name}: {msg}", flush=True)
        if status == "ok":
            ok += 1
        elif status == "skip":
            skip += 1
        else:
            fail += 1
        time.sleep(0.4)
    print(f"\nDONE ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
