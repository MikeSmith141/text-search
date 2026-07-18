#!/usr/bin/env python3
"""辽宋夏金补书：daizhige 下载 → 简体/轻清洗 → 有标点进 active，无标点进 _raw_no_punct。"""
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
ACTIVE = ROOT / "data" / "辽宋夏金"
RAW = ROOT / "data" / "_raw_no_punct"
META_PATH = ROOT / "data" / "books_meta.json"
MIN_PUNCT = 80
MIN_DENS = 0.02  # 标点密度门槛，低于则当无标点

cc = OpenCC("t2s")

VARIANT = str.maketrans(
    {
        "馀": "余",
        "餘": "余",
        "脩": "修",
        "眞": "真",
        "竝": "并",
        "碁": "棋",
        "呉": "吴",
        "撃": "击",
        "勅": "敕",
        "巻": "卷",
        "録": "录",
        "乆": "久",
        "隂": "阴",
        "䇿": "策",
        "㫖": "旨",
        "寜": "宁",
        "賛": "赞",
        "㨗": "捷",
        "頥": "颐",
        "槩": "概",
        "邉": "边",
        "峯": "峰",
        "祕": "秘",
        "舘": "馆",
    }
)

# name -> job
JOBS = {
    "宋史": {
        "paths": ["史藏/正史/宋史.txt"],
        "era": "元",
        "author": "脱脱等",
    },
    "辽史": {
        "paths": ["史藏/正史/辽史.txt"],
        "era": "元",
        "author": "脱脱等",
    },
    "金史": {
        "paths": ["史藏/正史/金史.txt"],
        "era": "元",
        "author": "脱脱等",
    },
    "续资治通鉴长编拾补": {
        "paths": ["史藏/编年/续资治通鉴长编拾补.txt"],
        "era": "清",
        "author": "黄以周等",
    },
    "契丹国志": {
        "paths": ["史藏/别史/契丹国志.txt"],
        "era": "南宋",
        "author": "叶隆礼",
    },
    # 以下 daizhige 为四库白文 / 无标点 → raw + 自动标点
    "宋史纪事本末": {
        "paths": ["史藏/纪事本末/宋史纪事本末.txt"],
        "era": "明",
        "author": "陈邦瞻",
        "force_raw": True,
    },
    "东都事略": {
        "paths": ["史藏/别史/东都事略.txt"],
        "era": "南宋",
        "author": "王称",
        "force_raw": True,
    },
    "大金国志": {
        "paths": ["史藏/别史/钦定重订大金国志.txt"],
        "era": "南宋",
        "author": "宇文懋昭（题）",
        "force_raw": True,
    },
}


def fetch(rel: str) -> str:
    url = REPO + "/" + urllib.parse.quote(rel)
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read()
            for enc in ("utf-8", "gb18030"):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    continue
            return b.decode("utf-8", errors="replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch fail {rel}: {last}")


def light_clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    lines = []
    blank = 0
    for ln in text.split("\n"):
        s = ln.rstrip().replace("\u3000", "").strip()
        if not s:
            blank += 1
            if blank <= 1:
                lines.append("")
            continue
        blank = 0
        if s.startswith("http://") or s.startswith("https://"):
            continue
        lines.append(s)
    text = "\n".join(lines).strip() + "\n"
    text = cc.convert(text)
    text = text.translate(VARIANT)
    for a, b in (("目録", "目录"), ("着录", "著录")):
        text = text.replace(a, b)
    return text


def punct_stats(text: str) -> tuple[int, float]:
    punct = len(re.findall(r"[，。！？；：、]", text))
    dens = punct / max(len(text), 1)
    return punct, dens


def main() -> None:
    ACTIVE.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    summary = []

    for name, job in JOBS.items():
        print(f"=== {name} ===", flush=True)
        parts = []
        for rel in job["paths"]:
            print(f"  fetch {rel}", flush=True)
            parts.append(fetch(rel))
            time.sleep(0.8)
        raw = "\n\n".join(parts)
        text = light_clean(raw)
        punct, dens = punct_stats(text)
        meta[name] = {"era": job["era"], "author": job["author"]}
        force_raw = bool(job.get("force_raw"))
        ok_punct = (not force_raw) and punct >= MIN_PUNCT and dens >= MIN_DENS

        if ok_punct:
            dest = ACTIVE / f"{name}.txt"
            dest.write_text(text, encoding="utf-8")
            status = "ACTIVE"
            print(f"  -> ACTIVE {dest} chars={len(text)} punct={punct} dens={dens:.4f}", flush=True)
        else:
            dest = RAW / f"{name}.txt"
            dest.write_text(text, encoding="utf-8")
            status = "RAW_NEED_PUNCT"
            print(
                f"  -> RAW {dest} chars={len(text)} punct={punct} dens={dens:.4f} force={force_raw}",
                flush=True,
            )
        summary.append(
            {
                "name": name,
                "status": status,
                "chars": len(text),
                "punct": punct,
                "dens": round(dens, 4),
                "label": f"{name}·[{job['era']}]·{job['author']}",
                "path": str(dest),
            }
        )

    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nSUMMARY", flush=True)
    for row in summary:
        print(
            f"  {row['status']:16} {row['label']} chars={row['chars']} punct={row['punct']} dens={row['dens']}",
            flush=True,
        )
    (ROOT / "logs" / "fetch_liaosong_batch.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
