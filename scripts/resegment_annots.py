#!/usr/bin/env python3
"""语义重分段：保护【】〈〉注释；合并碎句；按是岁/年号/季节/月份/干支/引书断段。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ANNOT_CHARS = set("【】〈〉")

ERA_NAMES = sorted(
    {
        "建隆",
        "乾德",
        "开宝",
        "太平兴国",
        "雍熙",
        "端拱",
        "淳化",
        "至道",
        "咸平",
        "景德",
        "大中祥符",
        "天禧",
        "乾兴",
        "天圣",
        "明道",
        "景祐",
        "宝元",
        "康定",
        "庆历",
        "皇祐",
        "至和",
        "嘉祐",
        "治平",
        "熙宁",
        "元丰",
        "元祐",
        "绍圣",
        "元符",
        "建中靖国",
        "崇宁",
        "大观",
        "政和",
        "重和",
        "宣和",
        "靖康",
        "建炎",
        "绍兴",
        "隆兴",
        "乾道",
        "淳熙",
        "绍熙",
        "庆元",
        "嘉泰",
        "开禧",
        "嘉定",
        "宝庆",
        "绍定",
        "端平",
        "嘉熙",
        "淳祐",
        "宝祐",
        "开庆",
        "景定",
        "咸淳",
        "德祐",
        "景炎",
        "祥兴",
        "天辅",
        "收国",
        "天会",
        "天眷",
        "皇统",
        "天德",
        "贞元",
        "正隆",
        "大定",
        "明昌",
        "承安",
        "泰和",
        "大安",
        "崇庆",
        "至宁",
        "贞祐",
        "兴定",
        "元光",
        "正大",
        "开兴",
        "天兴",
        "天赞",
        "天显",
        "会同",
        "大同",
        "天禄",
        "应历",
        "保宁",
        "乾亨",
        "统和",
        "开泰",
        "太平",
        "景福",
        "重熙",
        "清宁",
        "咸雍",
        "大康",
        "寿昌",
        "乾统",
        "天庆",
        "保大",
    },
    key=len,
    reverse=True,
)

GANZHI = {
    "甲子",
    "乙丑",
    "丙寅",
    "丁卯",
    "戊辰",
    "己巳",
    "庚午",
    "辛未",
    "壬申",
    "癸酉",
    "甲戌",
    "乙亥",
    "丙子",
    "丁丑",
    "戊寅",
    "己卯",
    "庚辰",
    "辛巳",
    "壬午",
    "癸未",
    "甲申",
    "乙酉",
    "丙戌",
    "丁亥",
    "戊子",
    "己丑",
    "庚寅",
    "辛卯",
    "壬辰",
    "癸巳",
    "甲午",
    "乙未",
    "丙申",
    "丁酉",
    "戊戌",
    "己亥",
    "庚子",
    "辛丑",
    "壬寅",
    "癸卯",
    "甲辰",
    "乙巳",
    "丙午",
    "丁未",
    "戊申",
    "己酉",
    "庚戌",
    "辛亥",
    "壬子",
    "癸丑",
    "甲寅",
    "乙卯",
    "丙辰",
    "丁巳",
    "戊午",
    "己未",
    "庚申",
    "辛酉",
    "壬戌",
    "癸亥",
}

MONTHS = sorted(
    [
        "正月",
        "二月",
        "三月",
        "四月",
        "五月",
        "六月",
        "七月",
        "八月",
        "九月",
        "十月",
        "十一月",
        "十二月",
    ],
    key=len,
    reverse=True,
)

YEAR_NUM = r"(?:元|[一二三四五六七八九十百零〇两]+|\d+)"


def protect_annots(text: str):
    tokens = []

    def repl(m):
        tokens.append(m.group(0))
        return f"⟦A{len(tokens)-1}⟧"

    out = re.sub(r"【[^】]*】", repl, text, flags=re.S)
    out = re.sub(r"〈[^〉]*〉", repl, out, flags=re.S)
    return out, tokens


def restore_annots(text: str, tokens):
    def repl(m):
        return tokens[int(m.group(1))]

    return re.sub(r"⟦A(\d+)⟧", repl, text)


def strip_wiki_chrome(text: str) -> str:
    text = re.sub(r"【[^】]*/卷\d+】", "", text)
    text = re.sub(r"七国攷卷一卷二→", "", text)
    text = re.sub(r"→+", "", text)
    return text


def is_break_start(s: str) -> bool:
    s = s.strip()
    if not s or s[0] in ANNOT_CHARS:
        return False
    if s.startswith(("是岁", "是年", "是春", "是夏", "是秋", "是冬", "是月")):
        return True
    for era in ERA_NAMES:
        if s.startswith(era) and len(s) > len(era):
            rest = s[len(era) :]
            if re.match(YEAR_NUM + r"年", rest):
                return True
            if re.match(YEAR_NUM + r"[春夏秋冬]", rest):
                return True
    for m in MONTHS:
        if s.startswith(m):
            return True
    if re.match(
        r"^[春夏秋冬](?:正月|二月|三月|四月|五月|六月|七月|八月|九月|十月|十一月|十二月|[，。\s])",
        s,
    ):
        if not s.startswith(("春秋", "春申", "夏商", "夏后")):
            return True
    if len(s) >= 2 and s[:2] in GANZHI:
        return True
    if re.match(r"^[^《〈【]{0,20}《[^》]+》\s*曰", s):
        return True
    return False


def find_inline_breaks(prot: str) -> list[int]:
    """在已 protect 的文本里，句末后若出现时间/年号等标记，插入断点位置。"""
    breaks = []
    # 句末字符后
    for m in re.finditer(r"[。！？；]", prot):
        j = m.end()
        rest = prot[j:]
        # 跳过空白（通常没有）
        if not rest:
            continue
        # 占位符开头不断
        if rest.startswith("⟦A"):
            continue
        if rest.startswith(("是岁", "是年", "是春", "是夏", "是秋", "是冬", "是月")):
            breaks.append(j)
            continue
        hit = False
        for era in ERA_NAMES:
            if rest.startswith(era):
                tail = rest[len(era) :]
                if re.match(YEAR_NUM + r"年", tail) or re.match(
                    YEAR_NUM + r"[春夏秋冬]", tail
                ):
                    breaks.append(j)
                    hit = True
                    break
        if hit:
            continue
        for mon in MONTHS:
            if rest.startswith(mon):
                breaks.append(j)
                hit = True
                break
        if hit:
            continue
        if len(rest) >= 2 and rest[:2] in GANZHI:
            breaks.append(j)
    return breaks


def soft_wrap(p: str, soft_max: int) -> list[str]:
    if len(p) <= soft_max:
        return [p]
    prot, tokens = protect_annots(p)
    chunks = re.split(r"(?<=[。！？])", prot)
    out: list[str] = []
    buf = ""
    for ch in chunks:
        if not ch:
            continue
        if buf and len(buf) + len(ch) > soft_max:
            cand = restore_annots(buf, tokens)
            if cand and cand[0] in ANNOT_CHARS and out:
                out[-1] += cand
            else:
                out.append(cand)
            buf = ch
        else:
            buf += ch
    if buf:
        cand = restore_annots(buf, tokens)
        if cand and cand[0] in ANNOT_CHARS and out:
            out[-1] += cand
        else:
            out.append(cand)
    return out or [p]


def resegment(raw: str, soft_max: int = 1000) -> str:
    raw = strip_wiki_chrome(raw)
    lines = raw.splitlines()
    headers: list[str] = []
    body: list[str] = []
    for line in lines:
        st = line.strip()
        if not body and (st.startswith("（本文件") or st.startswith("（来源") or st == ""):
            if st:
                headers.append(st)
            continue
        body.append(line)

    merged: list[str] = []
    for line in body:
        st = line.strip()
        if not st:
            continue
        if merged and st[0] in ANNOT_CHARS:
            merged[-1] += st
        else:
            merged.append(st)

    blob = "".join(merged)
    prot, tokens = protect_annots(blob)

    # 句末后时间标记断点
    cuts = set(find_inline_breaks(prot))
    # 同时按句末切成句子
    pieces: list[str] = []
    last = 0
    for m in re.finditer(r"[。！？]", prot):
        end = m.end()
        pieces.append(prot[last:end])
        last = end
        if end in cuts:
            pieces.append("§BR§")
    if last < len(prot):
        pieces.append(prot[last:])

    # 还原并组段
    sentences: list[str] = []
    for piece in pieces:
        if piece == "§BR§":
            sentences.append("§BR§")
            continue
        piece = piece.strip()
        if piece:
            sentences.append(restore_annots(piece, tokens))

    paragraphs: list[str] = []
    cur: list[str] = []
    for s in sentences:
        if s == "§BR§":
            if cur:
                paragraphs.append("".join(cur))
                cur = []
            continue
        if is_break_start(s) and cur:
            paragraphs.append("".join(cur))
            cur = [s]
        else:
            cur.append(s)
    if cur:
        paragraphs.append("".join(cur))

    final: list[str] = []
    for p in paragraphs:
        for piece in soft_wrap(p, soft_max):
            piece = piece.strip()
            if not piece:
                continue
            if final and piece[0] in ANNOT_CHARS:
                final[-1] += piece
            else:
                final.append(piece)

    # 首段 wiki【】残留
    if final and final[0][0] in ANNOT_CHARS:
        final[0] = re.sub(r"^【[^】]{0,80}】", "", final[0]).lstrip()
        if not final[0]:
            final = final[1:]
        elif final[0][0] in ANNOT_CHARS and len(final) > 1:
            final[1] = final[0] + final[1]
            final = final[1:]

    out: list[str] = []
    out.extend(headers)
    if headers:
        out.append("")
    for p in final:
        out.append(p)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def check(name: str, text: str):
    paras = [p for p in text.split("\n\n") if p.strip() and not p.startswith("（")]
    bad_p = sum(1 for p in paras if p and p[0] in ANNOT_CHARS)
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("（")]
    bad_l = sum(1 for l in lines if l and l[0] in ANNOT_CHARS)
    lens = [len(p) for p in paras] or [0]
    print(
        f"{name}: n={len(paras)} bad_p={bad_p} bad_l={bad_l} "
        f"max={max(lens)} avg={sum(lens)//len(lens)}"
    )
    for term in ["是岁", "是春", "是年", "天辅三年", "天辅二年", "八月", "九月"]:
        c = sum(1 for p in paras if p.startswith(term))
        if c:
            print(f"  段首{term}:{c}")
    if bad_p:
        for p in paras:
            if p and p[0] in ANNOT_CHARS:
                print("  BAD PARA:", p[:120])
                break
    if bad_l:
        for l in lines:
            if l and l[0] in ANNOT_CHARS:
                print("  BAD LINE:", l[:120])
                break
    return bad_p, bad_l


def main():
    jobs = [
        (
            Path("/root/projects/text-search/data/辽宋金夏/大金国志.txt"),
            Path("/root/projects/text-search/data/辽宋金夏/大金国志.txt.bak_reseg2"),
            900,
        ),
        (
            Path("/root/projects/text-search/data/先秦/七国考.txt"),
            Path("/root/projects/text-search/data/先秦/七国考.txt.bak_reseg2"),
            1000,
        ),
    ]
    for dest, bak, soft in jobs:
        raw = bak.read_text(encoding="utf-8") if bak.exists() else dest.read_text(encoding="utf-8")
        fixed = resegment(raw, soft_max=soft)
        dest.write_text(fixed, encoding="utf-8")
        check(dest.name, fixed)
        if "七国" in dest.name:
            i = fixed.find("春申")
            if i >= 0:
                print("  春申:", fixed[max(0, i - 15) : i + 100].replace("\n", " ↵ "))


if __name__ == "__main__":
    main()
