#!/usr/bin/env python3
"""修复自动标点在专名/年月中间的误断（大金国志等）。

策略（保守，避免把底本换行处的合法句号也删掉）：
  1) 词表回粘：地名/官制/年号中间的 ，。、
  2) 从无标点底本抽取「X州/府/军/县/京…」等做回粘
  3) 日期模式：天会四，年 → 天会四年；六，月 → 六月
  4) 语义逗号：归至东平，元帅府；知东平。六月；侵淮，从之
  5) 【】按语内部同样跑一轮
  6) 不重跑模型；不补引号

用法:
  python3 scripts/repair_false_punct.py \\
    --active data/辽宋夏金/大金国志.txt \\
    --raw data/_raw_no_punct/大金国志.txt
  --dry-run 只统计不写回
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

COMPOUNDS = sorted(
    {
        # 地名
        "东平",
        "东平府",
        "云中",
        "燕京",
        "西京",
        "东京",
        "南京",
        "汴京",
        "上京",
        "中京",
        "北京",
        "河朔",
        "燕云",
        "燕云河朔",
        "磁州",
        "单州",
        "沂州",
        "济南",
        "河南",
        "河北",
        "河东",
        "陕西",
        "山东",
        "山西",
        "两河",
        "中原",
        "江南",
        "江淮",
        "侵淮",
        "南伐",
        "渤海",
        "辽阳",
        "宁江",
        "沈州",
        "蔚州",
        "濵州",
        "潍州",
        "平州",
        "大名",
        "太原",
        "居庸",
        "居庸闗",
        "居庸关",
        "天祚",
        "归化",
        "奉圣",
        "宏州",
        "宁州",
        "徳州",
        "德州",
        "东胜",
        "天徳",
        "天德",
        "云内",
        "为我有",
        # 官署/官制
        "元帅府",
        "枢密院",
        "枢密院",
        "签书院",
        "中书枢密院",
        "中书枢密院",
        "燕京枢密院",
        "西京留守",
        "西京留守",
        "东京留守",
        "知东平",
        "知云中",
        "知济南",
        "院事",
        "府事",
        "父忧",
        "起复",
        "直枢密院",
        "直枢密院",
        "万户",
        "万户",
        "都统",
        "副都统",
        "通事",
        "节制",
        "州郡",
        "诸州郡",
        "汉服",
        "削发",
        "民兵",
        "守将",
        "守臣",
        "降于我",
        "至此",
        "同时",
        "从之",
        "颇异",
        "大举",
        "提兵",
        "附之",
        "用之",
        "签书院事",
        "枢密院事",
        "枢密院事",
        "中书枢密院事",
        "权中书枢密院事",
        "济南守",
        "磁单",
        "等州",
        "韩城",
        "符家口",
        "常胜军",
        # 帝号/谥号
        "海陵炀王",
        # 人名
        "高永昌",
        # 燕云交涉专名
        "燕山地",
        "燕山",
        "石晋",
        "故地",
        "石晋故地",
        "平营滦",
        "营平滦",
        "营平",
        "刘仁恭",
        "奉圣州",
        "赵良嗣",
        "马扩",
        "富勒结",
        "原约",
        "燕京",
        "山后",
        "山前",
        "蓟景",
        "景檀",
        "檀顺",
        "顺涿",
        "涿易",
        "军前",
        "报使",
        "岁币",
        "夹攻",
    },
    key=len,
    reverse=True,
)


HARD_FIXES = [
    # 帝号误断（用户点名）
    ("海陵，炀王", "海陵炀王"),
    ("海陵,炀王", "海陵炀王"),
    ("海陵，炀主", "海陵炀主"),  # 只去逗号，不改主/王
    ("海陵,炀主", "海陵炀主"),
    ("高。永昌", "高永昌"),
    ("高，永昌", "高永昌"),
    ("高、永昌", "高永昌"),
]


def apply_hard_fixes(text: str) -> str:
    for a, b in HARD_FIXES:
        text = text.replace(a, b)
    return text


def unsplit_word(text: str, w: str) -> str:
    if len(w) < 2:
        return text
    parts = [re.escape(w[0])]
    for c in w[1:]:
        parts.append(r"[，。、；：]*" + re.escape(c))
    return re.sub("".join(parts), w, text)


def unsplit_compounds(text: str) -> str:
    text = apply_hard_fixes(text)
    for w in COMPOUNDS:
        text = unsplit_word(text, w)
    return text


def unsplit_from_raw_lexicon(text: str, raw: str) -> str:
    """从无标点底本抽取真实连写专名，只回粘 raw 里确实连写的词。"""
    raw_plain = re.sub(r"[^\u4e00-\u9fff\u3400-\u4dbf]", "", raw)
    places = set(
        re.findall(
            r"[\u4e00-\u9fff]{1,2}(?:州|府|军|县|京|关|闗|郡|路|镇|寨|城)",
            raw_plain,
        )
    )
    for w in (
        "天祚",
        "云中",
        "东平",
        "河朔",
        "燕云",
        "南伐",
        "侵淮",
        "父忧",
        "起复",
        "院事",
        "元帅府",
        "都统",
        "万户",
        "万户",
        "通事",
        "签书",
        "枢密院",
        "枢密院",
        "留守",
        "留守",
        "为我有",
        "降于我",
        "归化",
        "奉圣",
        "东胜",
        "云内",
        "签书院事",
        "枢密院事",
    ):
        if w in raw_plain:
            places.add(w)
    # 只处理 raw 中确有的整词；禁止「平元帅府」这类跨词假专名
    for w in sorted(places, key=len, reverse=True):
        if len(w) < 2 or w not in raw_plain:
            continue
        # 禁止以 元帅/枢密 等官职被更长伪词吞掉（仅当整词在 raw 出现才行，已检查）
        text = unsplit_word(text, w)
    return text


def repair_pass(active: str, raw: str) -> tuple[str, dict]:
    t = apply_hard_fixes(active)
    # 先专名回粘，再语义逗号；每轮末再只做「确认在 raw 的词」回粘
    prev = None
    rounds = 0
    while prev != t and rounds < 8:
        prev = t
        t = unsplit_compounds(t)
        t = unsplit_from_raw_lexicon(t, raw)
        t = unsplit_dates(t)
        t = semantic_commas(t)
        t = repair_inside_annots(t)
        rounds += 1
    # 最后再补一次语义（防止词表把逗号挤掉后不回来）
    t = semantic_commas(t)
    t = unsplit_dates(t)
    return t, {"dict_rounds": rounds}


def unsplit_dates(text: str) -> str:
    eras = (
        r"(?:天会|天辅|天眷|皇统|天徳|天德|贞元|正隆|大定|明昌|承安|"
        r"泰和|大安|崇庆|至宁|贞祐|兴定|元光|正大|开兴|天兴|收国|"
        r"建炎|绍兴|乾道|淳熈|淳熙|庆元|嘉泰|开禧|嘉定|宝庆|绍定|端平|"
        r"重和|宣和|靖康|政和|天庆|保大)"
    )
    text = re.sub(
        rf"({eras})([元一二三四五六七八九十百]+)[，。、]+年", r"\1\2年", text
    )
    # 月份：只合「数+月」，不动「月，宋」这类合法句读
    text = re.sub(r"([正一二三四五六七八九十])[，。、]+月", r"\1月", text)
    text = re.sub(r"(十[一二]?)[，。、]+月", r"\1月", text)
    text = re.sub(
        r"(是年|是岁)[，。、]+([春夏秋冬正一二三四五六七八九十])", r"\1\2", text
    )
    return text


def semantic_commas(text: str) -> str:
    reps = [
        # —— 用户锚句专修 ——
        (r"归至东平元帅府", "归至东平，元帅府"),
        (r"至东平元帅府", "至东平，元帅府"),
        (r"诸州郡豫先", "诸州郡，豫先"),
        (r"州郡豫先", "州郡，豫先"),
        (r"降于我至此", "降于我，至此"),
        (r"除知东平([正一二三四五六七八九十]+月)", r"除知东平。\1"),
        (r"知东平([正一二三四五六七八九十]+月)", r"知东平。\1"),
        (r"不如式者死领", "不如式者死。领"),
        (r"者死领燕京", "者死。领燕京"),
        (r"六月行下", "六月，行下"),
        (r"削发及禁民汉服不如式者死", "削发及禁民汉服，不如式者死"),
        (r"为相同时", "为相，同时"),
        (r"为相同，时", "为相，同时"),
        (r"立爱主之尼雅满", "立爱主之。尼雅满"),
        (r"主之尼雅满", "主之。尼雅满"),
        (r"刘彦宗，卒并", "刘彦宗卒，并"),
        (r"刘彦宗卒并", "刘彦宗卒，并"),
        (r"彦宗卒并", "彦宗卒，并"),
        (r"于云中除", "于云中，除"),
        (r"留守乌珠", "留守。乌珠"),
        (r"留守乌珠", "留守。乌珠"),
        (r"侵淮从之", "侵淮，从之"),
        (r"从之【按", "从之。【按"),
        (r"之【按原书", "之。【按原书"),
        (r"民兵附之取", "民兵附之，取"),
        (r"附之取磁", "附之，取磁"),
        (r"博索渤海万户", "博索、渤海万户"),
        (r"博索渤海万户", "博索、渤海万户"),
        (r"博索。渤海", "博索、渤海"),
        (r"博索，渤海", "博索、渤海"),
        (r"托卜嘉汉军", "托卜嘉、汉军"),
        (r"托卜嘉。汉军", "托卜嘉、汉军"),
        (r"托卜嘉，汉军", "托卜嘉、汉军"),
        (r"王伯隆大起", "王伯隆，大起"),
        (r"以彦宗之，故", "以彦宗之故"),
        (r"以彦宗之故命", "以彦宗之故，命"),
        (r"之，故命", "之故，命"),
        (r"签书院事【按", "签书院事。【按"),
        (r"院事【按金史", "院事。【按金史"),
        (r"父忧，起复", "父忧起复"),
        (r"父忧。起复", "父忧起复"),
        (r"直枢密院与此颇异", "直枢密院，与此颇异"),
        (r"济南，守", "济南守"),
        (r"济南。守", "济南守"),
        (r"刘筈：传", "刘筈传"),
        (r"刘筈，传", "刘筈传"),
        # 获天祚于是 → 获天祚。于是（raw 同段也可加句读）
        (r"获天祚于是", "获天祚。于是"),
        (r"为我有。后", "为我有。后"),
        (r"为我有后", "为我有。后"),
        (r"帝，崩尼雅满", "帝崩。尼雅满"),
        (r"武元帝崩尼雅满", "武元帝崩。尼雅满"),
        # 双保险专名
        (r"云。中", "云中"),
        (r"云，中", "云中"),
        (r"东。平", "东平"),
        (r"东，平", "东平"),
        (r"西。京", "西京"),
        (r"东。京", "东京"),
        (r"南。京", "南京"),
        (r"河。朔", "河朔"),
        (r"燕。云", "燕云"),
        (r"元帅，府", "元帅府"),
        (r"枢密院。事", "枢密院事"),
        (r"枢密，院", "枢密院"),
        (r"州。郡", "州郡"),
        (r"父，忧", "父忧"),
        (r"颇。异", "颇异"),
        (r"南，伐", "南伐"),
        (r"侵，淮", "侵淮"),
        (r"磁。单", "磁单"),
        (r"等，州", "等州"),
        (r"取。磁", "取磁"),
        (r"蔡之。后", "蔡之后"),
        (r"围蔡之。后", "围蔡之后"),
        (r"天。祚", "天祚"),
        (r"天，祚", "天祚"),
        (r"归。化", "归化"),
        (r"奉。圣", "奉圣"),
        (r"东。胜", "东胜"),
        (r"天。徳", "天德"),
        (r"天。德", "天德"),
        (r"者。死领", "者死。领"),
        (r"式者。死", "式者死"),
        (r"主。之", "主之"),
        # —— 十一月议割燕山（用户锚句）——
        (r"十一月遣使", "十一月，遣使"),
        (r"十二月遣使", "十二月，遣使"),
        (r"([正一二三四五六七八九十]月)遣使", r"\1，遣使"),
        (r"使于，宋", "使于宋"),
        (r"使于宋议", "使于宋，议"),
        (r"燕山。地", "燕山地"),
        (r"燕山地，初", "燕山地。初"),
        (r"燕山地。初宋", "燕山地。初，宋"),
        (r"与我，约", "与我约"),
        (r"与我约但求", "与我约，但求"),
        (r"但求。石晋", "但求石晋"),
        (r"石晋故。地", "石晋故地"),
        (r"故地，初不思", "故地，初不思"),
        (r"故地初不思", "故地，初不思"),
        (r"不思平。营", "不思平营"),
        (r"平。营滦", "平营滦"),
        (r"平营滦三州乃", "平营滦三州，乃"),
        (r"刘仁。以遗", "刘仁恭以遗"),  # 脱「恭」时尽量粘
        (r"赵良嗣。马扩", "赵良嗣、马扩"),
        (r"赵良嗣，马扩", "赵良嗣、马扩"),
        (r"不论。原约", "不论原约"),
        (r"不论原约特与", "不论原约，特与"),
        (r"蓟。景。檀。顺。涿易", "蓟景檀顺涿易"),
        (r"蓟。景", "蓟景"),
        (r"景。檀", "景檀"),
        (r"檀。顺", "檀顺"),
        (r"顺。涿", "顺涿"),
        (r"但谓蓟景檀顺涿易也", "但谓蓟、景、檀、顺、涿、易也"),
        (r"营平。滦", "营平滦"),
        (r"四军大。王", "四军大王"),
        (r"契。丹", "契丹"),
        # 十一月另起段由 resegment 负责；这里保证月名不被切开
        (r"十[，。]([一二])月", r"十\1月"),
        (r"正[，。]月", "正月"),
    ]
    for a, b in reps:
        text = re.sub(a, b, text)
    return text


def repair_inside_annots(text: str) -> str:
    def fix_block(m: re.Match) -> str:
        inner = m.group(1)
        prev = None
        while prev != inner:
            prev = inner
            inner = unsplit_compounds(inner)
            inner = unsplit_dates(inner)
            inner = semantic_commas(inner)
        return "【" + inner + "】"

    return re.sub(r"【([^】]*)】", fix_block, text)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--active", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    active_p = Path(args.active)
    raw_p = Path(args.raw)
    active = active_p.read_text(encoding="utf-8")
    raw = raw_p.read_text(encoding="utf-8")
    fixed, stats = repair_pass(active, raw)
    print("stats", stats)
    print("len", len(active), "->", len(fixed), "delta", len(fixed) - len(active))

    i = fixed.find("尼雅满自")
    # prefer 四月句
    j = fixed.find("四月，尼雅满自")
    if j >= 0:
        i = j
    if i >= 0:
        a = fixed.rfind("\n\n", 0, i)
        b = fixed.find("\n\n", i)
        print("--- sample ---")
        print(fixed[a + 2 if a >= 0 else 0 : b if b >= 0 else i + 500][:1000])
        print("--- end ---")

    checks = [
        "归至东平，元帅府",
        "知东平府",
        "诸州郡，豫先",
        "降于我，至此",
        "知东平。六月",
        "六月，行下",
        "枢密院事刘彦宗",
        "云中，除",
        "天会四年",
        "父忧",
        "知云中兼西京",
        "侵淮，从之",
        "是年六月",
        "取磁单等州",
        "彦宗之故，命",
        "不如式者死。领",
    ]
    ok = sum(1 for c in checks if c in fixed)
    for c in checks:
        print(("OK" if c in fixed else "MISS"), c)
    print(f"checks {ok}/{len(checks)}")

    if args.dry_run:
        return
    bak = active_p.with_suffix(active_p.suffix + ".bak_before_punct_repair")
    if not bak.exists():
        bak.write_text(active, encoding="utf-8")
        print("backup", bak)
    active_p.write_text(fixed, encoding="utf-8")
    print("wrote", active_p)


if __name__ == "__main__":
    main()
