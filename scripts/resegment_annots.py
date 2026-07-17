#!/usr/bin/env python3
"""语义重分段：保护【】〈〉注释；合并碎句。

style:
  chrono  — 编年体：是岁/年号/季节/月份/干支/引书/史料：/按
  kaoju  — 考据体（七国考）：词条+史料：拆分、按、又；不用年号季节干支
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ANNOT_CHARS = set("【】〈〉")

# 编年体年号干支标：【甲午】【乙未】—— 是叙事年份，不是【按…】类注释
# 用户定稿：这种必须另起一段；禁止单独【丙申】。再下一段才写年事
GZ_STEM = r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]"
GZ_YEAR_MARK_RE = re.compile(rf"【({GZ_STEM})】")
GZ_YEAR_MARK_START_RE = re.compile(rf"^【{GZ_STEM}】")
GZ_YEAR_MARK_LONELY_RE = re.compile(rf"^【{GZ_STEM}】[。．，、：:\"”」』]*$")

# 卷次（大金国志等四库本）：卷尾可去，卷首另起段
# 编号必须长优先，否则「卷三十七」会误切成「卷三」
VOL_CN = r"[首一二三四五六七八九十百零〇两\d]+"  # 目录 split 宽松
VOL_NUM = r"(?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首)"
VOL_START_RE = re.compile(
    r"(?:钦定四库全书)?钦定重订大金国志卷(?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首)"
)
# 卷名标题本体（到卷首/卷N 为止，后面正文另段）
VOL_TITLE_ONLY_RE = re.compile(
    r"^((?:钦定四库全书)?钦定重订大金国志(?:卷首|卷(?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首)))(.*)$"
)
# 卷尾+卷首粘连
VOL_TAIL_BEFORE_NEXT_RE = re.compile(
    r"钦定重订大金国志卷(?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首)"
    r"(?=(?:钦定四库全书)?钦定重订大金国志[卷春](?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首))"
)
SIKU_VOL_START_RE = re.compile(
    rf"钦定四库全书[^\n。]{{0,30}}?卷{VOL_CN}"
)
VOL_TAIL_ONLY_RE = re.compile(
    r"^钦定重订大金国志卷(?:四十一|四十|三十[一二三四五六七八九]?|二十[一二三四五六七八九]?|十[一二三四五六七八九]?|[一二三四五六七八九]|首)$"
)

# 大金国志开卷目录：粘连 TOC → 每卷一行
DAJIN_TOC_START = "钦定四库全书史部"
DAJIN_TIYAO_MARK = "【臣】等谨案"
DAJIN_BODY_AFTER_FRONT = re.compile(
    r"钦定四库全书钦定重订大金国志卷首大金初兴本末金国本名"
)


def expand_dajin_toc_front(text: str) -> str:
    """把开卷「史部四+目录+卷一…卷四十一」粘连块拆成用户样例的多段。

    目录每卷一行；【臣】等谨案提要另段；乾隆恭校上另段。
    """
    if DAJIN_TOC_START not in text or "大金国志目录" not in text[:2000]:
        return text

    start = text.find(DAJIN_TOC_START)
    # 正文卷首（非目录）：…陆费墀。钦定四库全书钦定重订大金国志卷首大金初兴本末金国本名
    m_body = DAJIN_BODY_AFTER_FRONT.search(text)
    if not m_body or m_body.start() <= start:
        # 退化：到第一个「钦定四库全书钦定重订大金国志卷首」且后接「金国本名」
        m_body = re.search(
            r"钦定(?:四库全书)?钦定重订大金国志卷首(?=大金初兴本末金国本名|大金初兴本末金国)",
            text,
        )
    if not m_body or m_body.start() <= start:
        end_front = text.find("陆费墀")
        if end_front < 0:
            return text
        end_front = text.find("。", end_front)
        if end_front < 0:
            return text
        end_front += 1
    else:
        end_front = m_body.start()

    front = text[start:end_front]
    rest = text[end_front:]

    # 提要起点
    tiyao_i = front.find(DAJIN_TIYAO_MARK)
    if tiyao_i < 0:
        tiyao_i = front.find("等谨案钦定重订大金国志")
        if tiyao_i > 0:
            # 补回可能被吞的【臣】
            pass
    if tiyao_i < 0:
        return text

    toc = front[:tiyao_i]
    tiyao = front[tiyao_i:]

    # 修常见粘连/脱字
    toc = toc.replace("卷宣宗皇帝", "卷二十四宣宗皇帝")
    toc = re.sub(r"海陵[\uf847]?王", "海陵王", toc)
    toc = toc.replace("\ue5ab", "")  # 皂下坏字

    lines: list[str] = []
    # 史部四
    m = re.match(r"^(钦定四库全书史部[四五六七八]?)", toc)
    if m:
        lines.append(m.group(1))
        toc = toc[m.end() :]
    # 目录别史类
    m = re.match(r"^(钦定重订大金国志目录别史类)", toc)
    if m:
        lines.append(m.group(1))
        toc = toc[m.end() :]

    # 卷首 / 卷一…卷四十一 — 在「卷X」前切
    # 卷首后可带 大金初兴本末金九帝年谱
    parts = re.split(rf"(?=卷{VOL_CN}|卷首)", toc)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 卷二十七/二十八/二十九 人名表：功臣、翰苑后加顿号感的冒号（用户样例）
        p = re.sub(
            r"^(卷二十七开国功臣)(?=[尼固斡富乌])",
            r"\1：",
            p,
        )
        p = re.sub(
            r"^(卷二十八文学翰苑上)(?=[宇蔡高髙马施郝李王刘杨史萧冯梁韩])",
            r"\1：",
            p,
        )
        p = re.sub(
            r"^(卷二十九文学翰苑下)(?=[王麻高髙张董胥路耶李党赵周])",
            r"\1：",
            p,
        )
        # 卷三十二 去多余逗号
        p = p.replace("印宝，宗族", "印宝宗族")
        lines.append(p)

    # 提要：【臣】等谨案…抵牾若此。今恭依… / 乾隆…陆费墀。
    tiyao = tiyao.strip()
    # 确保【臣】前缀
    if tiyao.startswith("等谨案"):
        tiyao = "【臣】" + tiyao
    # 粘连「直斥。其号」→「直斥其号」（用户样例合并断句）
    tiyao = re.sub(r"直斥。\s*其号", "直斥其号", tiyao)
    # 提要压成单行，避免 auto-punct 的「一句一行」把提要拆碎
    tiyao = re.sub(r"\s+", "", tiyao)
    # 乾隆恭校另段
    g = re.search(r"(乾隆.{0,40}恭校上.*)$", tiyao)
    tiyao_main = tiyao
    tiyao_tail = ""
    if g:
        tiyao_main = tiyao[: g.start()].rstrip()
        tiyao_tail = g.group(1).strip()
    # 主提要末补句号
    if tiyao_main and tiyao_main[-1] not in "。！？":
        if tiyao_main.endswith("焉"):
            tiyao_main += "。"

    blocks = lines + [tiyao_main]
    if tiyao_tail:
        blocks.append(tiyao_tail)

    # 用双换行插入，后续 resegment 会按空行/句读再整理；先保证目录各行独立
    expanded = "\n\n".join(blocks)
    return text[:start] + expanded + "\n\n" + rest.lstrip()


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

# 史料/传注开头（七国考等考据体）
SOURCE_TITLES = sorted(
    {
        "史记",
        "汉书",
        "后汉书",
        "左传",
        "春秋左传",
        "国策",
        "国䇿",
        "战国策",
        "通鉴",
        "资治通鉴",
        "通典",
        "通志",
        "华阳国志",
        "玉海",
        "物原",
        "风俗通",
        "汉旧仪",
        "列仙传",
        "商君传",
        "刺客传",
        "蒙恬传",
        "白起传",
        "李斯传",
        "荆轲传",
        "司马迁传",
        "范睢传",
        "正义",
        "集仙传",
        "汉官仪",
        "秦纪",
        "秦本纪",
        "竹书纪年",
        "吕氏春秋",
        "韩诗外传",
    },
    key=len,
    reverse=True,
)

# 粘连时也可在标题前硬断：…卫尉史记： → 在「史记：」前断
# 注意：不能用过宽的「X传：」吞掉「左尹左传：」——用 find_source_colon_spans 精确找
SOURCE_COLON_RE = re.compile(
    r"(?:"
    + "|".join(re.escape(x) for x in SOURCE_TITLES)
    + r"|[\u4e00-\u9fff]{1,4}传"
    + r")[：:]"
)


def find_source_colon_spans(text: str) -> list[tuple[int, int, str]]:
    """返回 (start, end, matched含冒号)。已知书名优先，避免「左尹左传：」整吞。

    另识别简写「策」=战国策：`策：` 或词条/句读后的 `策卫鞅…`。
    词条尾字不能被吃进书名：相国策 ≠ 国策。
    """
    spans: list[tuple[int, int, str]] = []
    i = 0
    n = len(text)

    def at_src_boundary(pos: int) -> bool:
        """书名起点：句首，或前字非汉字（词条已在前段拆开）。"""
        if pos == 0:
            return True
        prev = text[pos - 1]
        if prev in "。！？；\n」』\"'）】〉:：":
            return True
        # 保护块边界
        if prev == "⟧":
            return True
        # 前为汉字 → 可能是词条粘连，不算书名起点（交给 lemma 拆）
        if "\u4e00" <= prev <= "\u9fff":
            return False
        return True

    while i < n:
        if text[i] == "⟦":
            j = text.find("⟧", i)
            i = n if j < 0 else j + 1
            continue
        hit = None
        for title in SOURCE_TITLES:
            if not text.startswith(title, i):
                continue
            if not at_src_boundary(i):
                continue
            after = i + len(title)
            if after < n and text[after] in "：:":
                hit = (i, after + 1, text[i : after + 1])
                break
            if title in ("汉书", "后汉书", "正义", "汉旧仪", "风俗通"):
                window = text[after : after + 12]
                m = re.match(r".{0,10}?[：:]", window)
                if m and ("曰" in m.group(0) or "云" in m.group(0) or "表" in m.group(0)):
                    end = after + m.end()
                    hit = (i, end, text[i:end])
                    break
            # 国策/国䇿 可无冒号：国策卫鞅…
            if title in ("国策", "国䇿", "战国策") and after < n and "\u4e00" <= text[after] <= "\u9fff":
                hit = (i, after, text[i:after])
                break
        # 简写 策 = 战国策（策： / 策卫鞅）
        if hit is None and text.startswith("策", i):
            after = i + 1
            prev = text[i - 1] if i > 0 else ""
            ok_prev = prev == "" or prev in "。！？；\n」』\"'）】〉"
            if not ok_prev and "\u4e00" <= prev <= "\u9fff":
                k = i
                while k > 0 and "\u4e00" <= text[k - 1] <= "\u9fff" and (i - k) < 6:
                    k -= 1
                lemma = text[k:i]
                if 2 <= len(lemma) <= 6 and lemma not in ("决策", "政策", "策略", "对策", "策划"):
                    if re.search(
                        r"(?:国|相|尹|尉|君|侯|令|卿|官|史|丞|士|徒|医|簿)$",
                        lemma,
                    ):
                        ok_prev = True
            if ok_prev and after < n:
                if text[after] in "：:":
                    hit = (i, after + 1, text[i : after + 1])
                elif "\u4e00" <= text[after] <= "\u9fff":
                    hit = (i, after, "策")
        if hit is None and at_src_boundary(i):
            m = re.match(r"([\u4e00-\u9fff]{1,4}传)[：:]", text[i:])
            if m:
                body = m.group(1)
                if not any(body.endswith(t) and body != t for t in SOURCE_TITLES):
                    if body not in SOURCE_TITLES:
                        hit = (i, i + m.end(), m.group(0))
        if hit:
            spans.append(hit)
            i = hit[1]
        else:
            i += 1
    return spans


# 「按…」起首（按物原、按周礼、按：、余按）
AN_START_RE = re.compile(r"^(?:余)?按")

# 又 + 引书/按（考据体：又左传有…）
YOU_SOURCE_RE = re.compile(
    r"又(?:左传|国策|国䇿|策|史记|汉书|通鉴|战国策|华阳国志|通典|通志|按|《|余按)"
)

# 词条：史料名冒号前 2–4 字官名/条目（右尹史记：→ 右尹 / 史记：）
LEMMA_CHARS = re.compile(r"[\u4e00-\u9fff]")

# 名词解释条目标记：…尹/尉/相/君/侯…（廷尉。/都尉。/客卿。）
LEMMA_TAIL = (
    r"(?:尹|尉|相|君|侯|令|正|簿|医|卜|徒|卿|士|官|史|"
    r"司马|司徒|司空|司宫|司寇|丞相|大夫|将军|太守|县令|"
    r"中尉|主簿|侍医|掌卜|户籍|沟渠|租禾|诸侯|客卿|亚卿|"
    r"廷尉|都尉|太尉|国尉|军尉|长史|大良造)"
)
# 「。廷尉。」「。都尉。」 句：纯名词 + 句号（2–6 字，避免 自卿相。）
LEMMA_SENT_RE = re.compile(
    rf"(?<=[。！？；」』\"'])([\u4e00-\u9fff]{{2,6}})。"
)
LEMMA_OK_RE = re.compile(
    rf"^[\u4e00-\u9fff]{{2,6}}(?:{LEMMA_TAIL})$|^"
    + LEMMA_TAIL
    + r"$|"
    r"^(?:中尉|主簿|侍医|掌卜|户籍|沟渠|租禾|诸侯|客卿|亚卿|"
    r"廷尉|都尉|太尉|国尉|军尉|长史|大良造|左右丞相|昌平君|"
    r"信陵君|平原君|春申君|华阳君|平阳君|武襄君|长信侯|"
    r"军正|工正|廷理|持节尉|通侯|大司马|右司马|左司马)$"
)

# 等级/爵序词：按礼段内「下大夫。上士。」是罗列，不是词条头
RANK_LIST_LEMMAS = {
    "卿",
    "下大夫",
    "上大夫",
    "中大夫",
    "上士",
    "中士",
    "下士",
    "大夫",
    "上卿",
    "中卿",
    "下卿",
    "公孤",
}


def looks_like_lemma(word: str) -> bool:
    """是否像名词解释词条（官职/封号等）。"""
    w = word.strip().rstrip("。")
    if not (2 <= len(w) <= 6):
        return False
    if w in RANK_LIST_LEMMAS:
        return False
    if any(x in w for x in "之乎也者以其而于自注云曰为"):
        return False
    if w in SOURCE_TITLES:
        return False
    if w in (
        "相国",
        "左右丞相",
        "客卿",
        "亚卿",
        "廷尉",
        "都尉",
        "太尉",
        "国尉",
        "军尉",
    ):
        return True
    if LEMMA_OK_RE.match(w):
        return True
    if re.search(
        r"(?:尹|尉|相|君|侯|令|正|簿|医|卜|徒|司马|司徒|司空|司宫|丞相)$",
        w,
    ):
        return True
    return False


# 卷首 / 门类
VOL_HEAD_RE = re.compile(
    r"(钦定四库全书七国[攷考]卷[一二三四五六七八九十百零〇两\d]+[^\n。]{0,20}撰。)"
)
SECTION_HEAD_RE = re.compile(
    r"([秦楚齐燕赵魏韩](?:职官|食货|兵制|都邑|地理|田赋|官制|宫室|礼制|刑法)"
    r"(?:〈[^〉]{0,40}〉)?)"
)
# 词条后紧接 策/国策/史记 等：相国策… / 相国史记…
LEMMA_BEFORE_SRC_RE = re.compile(
    r"(?<![\u4e00-\u9fff])"
    r"([\u4e00-\u9fff]{2,6})"
    r"(?=(?:国策|国䇿|策|史记|汉书|左传|通鉴|通典|通志|华阳国志|正义))"
)
# 仅书/注家 X曰" 起段（不含 孙叔敖曰 等对话）
SPEECH_OPEN_RE = re.compile(
    r"((?:荀子|淮南子|孟子|庄子|列子|管子|韩非子|"
    r"杜预|徐广|服虔|孔颖达|正义|通典|通志|"
    r"韦昭|颜师古|司马贞|张守节|鲍彪|吴师道)曰\")"
)
SPEECH_CLOUD_RE = re.compile(r"((?:物原|玉海|风俗通|汉旧仪)云\")")
# 粘连 相。秦按礼： → 在 按 前断
AN_LI_RE = re.compile(r"(?:^|[。！？；])(?:秦|楚|齐|燕|赵|魏|韩)?(按(?:礼|周礼|物原)[：:]?)")


def is_speech_open_worth_break(matched: str, prev_char: str) -> bool:
    """知名书/注家的 曰\"/云\" 才断。"""
    return matched.startswith(
        (
            "荀子曰",
            "淮南子曰",
            "孟子曰",
            "庄子曰",
            "列子曰",
            "杜预曰",
            "徐广曰",
            "正义曰",
            "通典曰",
            "通志曰",
            "物原云",
            "玉海云",
        )
    )


def is_gz_year_mark_start(s: str) -> bool:
    """段首是否为年号干支标【甲午】（可另起一段；不同于【按…】注释）。"""
    return bool(GZ_YEAR_MARK_START_RE.match((s or "").strip()))


def protect_annots(text: str):
    """保护【按…】/〈…〉注释；年号干支标【甲午】不保护，便于断段。"""
    year_marks: list[str] = []

    def save_ym(m):
        year_marks.append(m.group(0))
        return f"⟦Y{len(year_marks)-1}⟧"

    # 先抽出纯【干支】，避免被当成普通注释吞掉
    staged = GZ_YEAR_MARK_RE.sub(save_ym, text)

    tokens: list[str] = []

    def repl(m):
        tokens.append(m.group(0))
        return f"⟦A{len(tokens)-1}⟧"

    out = re.sub(r"【[^】]*】", repl, staged, flags=re.S)
    out = re.sub(r"〈[^〉]*〉", repl, out, flags=re.S)

    # 还原年号干支标为明文，供 find_gz_year_breaks / is_break_start 识别
    def rest_ym(m):
        return year_marks[int(m.group(1))]

    out = re.sub(r"⟦Y(\d+)⟧", rest_ym, out)
    return out, tokens


def restore_annots(text: str, tokens):
    def repl(m):
        return tokens[int(m.group(1))]

    return re.sub(r"⟦A(\d+)⟧", repl, text)


def normalize_gz_year_marks(text: str) -> str:
    """【丙申】。收国二年 / 【丙申】。\\n收国 → 去掉干支标后的误断句号，便于与年事粘合。"""
    # 干支标后紧跟句号/顿号，再接年号、季节、是岁等年事 → 删误点
    text = re.sub(
        rf"(【{GZ_STEM}】)[。．](?=[\s\u3000]*"
        rf"(?:收国|天辅|天会|天眷|皇统|天徳|天德|贞元|正隆|大定|明昌|承安|"
        rf"泰和|大安|崇庆|至宁|贞祐|兴定|元光|正大|开兴|天兴|"
        rf"是岁|是年|是春|是夏|是秋|是冬|是月|"
        rf"春|夏|秋|冬|"
        rf"正[月月]|十[一二]?月|[一二三四五六七八九]月|"
        rf"{GZ_STEM}|"
        rf"太祖|太宗|帝))",
        r"\1",
        text,
    )
    # 跨行：【丙申】。\n收国二年 → 【丙申】收国二年（中间空白去掉，句号已在上式处理时若同行）
    text = re.sub(
        rf"(【{GZ_STEM}】)[。．]?\s*\n\s*(?="
        rf"(?:收国|天辅|天会|天眷|皇统|天徳|天德|贞元|正隆|大定|明昌|承安|"
        rf"泰和|大安|崇庆|至宁|贞祐|兴定|元光|正大|开兴|天兴|"
        rf"是岁|是年|春|夏|秋|冬))",
        r"\1",
        text,
    )
    return text


def find_gz_year_breaks(prot: str) -> list[int]:
    """正文中的【甲午】【乙未】等年号干支标前强制断段。"""
    breaks: list[int] = []
    for m in GZ_YEAR_MARK_RE.finditer(prot):
        if m.start() > 0:
            breaks.append(m.start())
    return breaks


def merge_lonely_gz_year_marks(paragraphs: list[str]) -> list[str]:
    """禁止【丙申】。/【戊戌】\" 单独成段：与下一段年事合并为【丙申】收国二年…"""
    out: list[str] = []
    i = 0
    n = len(paragraphs)
    while i < n:
        p = paragraphs[i].strip()
        m = GZ_YEAR_MARK_LONELY_RE.match(p)
        if m and i + 1 < n:
            nxt = paragraphs[i + 1].strip()
            # 不并到卷名/目录/纪年概括
            if (
                nxt
                and not is_volume_start(nxt)
                and not re.match(rf"^卷{VOL_CN}", nxt)
                and not nxt.startswith("卷首")
                and not nxt.startswith("纪年")
                and not nxt.startswith("钦定四库全书史部")
                and not nxt.startswith("钦定重订大金国志目录")
                and not nxt.startswith(DAJIN_TIYAO_MARK)
                and not nxt.startswith("【臣】等谨案")
                and not re.match(r"^乾隆\d+年", nxt)
            ):
                mark_m = GZ_YEAR_MARK_RE.match(p)
                mark = mark_m.group(0) if mark_m else p
                # 去掉下段误起的开引号
                if nxt and nxt[0] in "\"“「『":
                    nxt = nxt[1:]
                out.append(mark + nxt)
                i += 2
                continue
        out.append(paragraphs[i])
        i += 1
    return out


def strip_wiki_chrome(text: str) -> str:
    text = re.sub(r"【[^】]*/卷\d+】", "", text)
    text = re.sub(r"七国攷卷一卷二→", "", text)
    text = re.sub(r"→+", "", text)
    return text


def is_source_colon_start(s: str) -> bool:
    """史记：/李斯传：/策：/策卫鞅… 等史料起首。"""
    s = s.strip()
    if not s:
        return False
    # 简写策（战国策）
    if s.startswith("策：") or s.startswith("策:"):
        return True
    if re.match(r"^策[\u4e00-\u9fff]", s):
        return True
    if s.startswith(("国策", "国䇿", "战国策")):
        return True
    spans = find_source_colon_spans(s[:40])
    return bool(spans and spans[0][0] == 0)


def is_an_start(s: str) -> bool:
    """按 / 余按 / 按： 起首（非「秦按礼」——须以按开头）。"""
    s = s.strip()
    if not s:
        return False
    return bool(AN_START_RE.match(s))


def is_you_start(s: str) -> bool:
    """又… 起首（考据体补充）。"""
    s = s.strip()
    return bool(s) and s.startswith("又")


def is_relative_year_start(s: str) -> bool:
    """次年三月 / 明年春 / 是年夏 等相对纪年起首。"""
    s = s.strip()
    if not s:
        return False
    if re.match(r"^次年(?:[春夏秋冬]|正|十[一二]?|[一二三四五六七八九])?月?", s):
        # 次年 / 次年春 / 次年三月
        if s.startswith("次年"):
            return True
    if re.match(r"^明年(?:[春夏秋冬]|正|十[一二]?|[一二三四五六七八九])?月?", s):
        if s.startswith("明年"):
            return True
    if re.match(r"^翌年", s):
        return True
    return False


def is_speech_start(s: str) -> bool:
    """仅书/注家 曰\" 起首，不含对话人物。"""
    s = s.strip()
    return bool(
        re.match(
            r"^(?:荀子|淮南子|孟子|庄子|列子|管子|韩非子|"
            r"杜预|徐广|服虔|孔颖达|正义|通典|通志|"
            r"韦昭|颜师古|鲍彪|吴师道)曰\"",
            s,
        )
        or re.match(r"^(?:物原|玉海|风俗通|汉旧仪)云\"", s)
    )


def is_break_start(s: str, style: str = "chrono") -> bool:
    s = s.strip()
    if not s:
        return False
    # 年号干支标【甲午】可起段（须先于「禁【起首」）
    if style != "kaoju" and is_gz_year_mark_start(s):
        return True
    if s[0] in ANNOT_CHARS:
        return False
    if is_volume_start(s):
        return True
    if is_an_start(s):
        return True
    if is_source_colon_start(s):
        return True
    if style == "kaoju":
        if is_you_start(s):
            return True
        if is_speech_start(s):
            return True
        # 卷首 / 门类
        if s.startswith("钦定四库全书"):
            return True
        if re.match(
            r"^[秦楚齐燕赵魏韩](?:职官|食货|兵制|都邑|地理|田赋|官制|宫室|礼制|刑法)",
            s,
        ):
            return True
        # 名词条：廷尉 / 廷尉。 / 右尹 / 相国 — 不含等级罗列词
        bare = s.rstrip("。")
        if looks_like_lemma(bare) and (s == bare or s == bare + "。"):
            return True
        return False
    # chrono
    if s.startswith(("是岁", "是年", "是春", "是夏", "是秋", "是冬", "是月")):
        return True
    if is_relative_year_start(s):
        return True
    for era in ERA_NAMES:
        if s.startswith(era) and len(s) > len(era):
            rest = s[len(era) :]
            if re.match(YEAR_NUM + r"年", rest):
                return True
            if re.match(YEAR_NUM + r"[春夏秋冬]", rest):
                return True
    for mon in MONTHS:
        if s.startswith(mon):
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


def peel_lemma_before(prot: str, j: int) -> int | None:
    """若 j 前是短词条（右尹史记：/相国策 的「右尹」「相国」），返回词条起点。"""
    if j <= 0:
        return None
    source_prefix = prot[j : j + 8]
    k = j
    while k > 0 and (j - k) < 6 and LEMMA_CHARS.match(prot[k - 1] or ""):
        k -= 1
    n = j - k
    if n < 2 or n > 6:
        return None
    lemma = prot[k:j]
    if lemma in ("相国", "左右丞相", "客卿", "廷尉", "都尉", "太尉"):
        return k
    if not looks_like_lemma(lemma):
        return None
    if source_prefix.startswith("史记") and lemma.endswith("史"):
        return None
    return k


def find_lemma_sentence_breaks(prot: str) -> list[int]:
    """「。廷尉。」「。都尉。」：在名词前断。跳过等级罗列与引号内。"""
    breaks: list[int] = []
    in_quote = [False] * len(prot)
    openers = set('"“「『')
    closers = set('"”」』')
    depth = 0
    for i, ch in enumerate(prot):
        if ch in openers:
            depth += 1
        if depth > 0:
            in_quote[i] = True
        if ch in closers and depth > 0:
            depth -= 1

    for m in LEMMA_SENT_RE.finditer(prot):
        word = m.group(1)
        if in_quote[m.start(1)]:
            continue
        if not looks_like_lemma(word):
            continue
        after = prot[m.end() : m.end() + 12]
        if re.match(r"[\u4e00-\u9fff]{1,4}侯。", after) and word.endswith("侯"):
            continue
        before = prot[max(0, m.start(1) - 12) : m.start(1)]
        if word.endswith("侯") and re.search(r"[\u4e00-\u9fff]{1,4}侯。$", before):
            continue
        breaks.append(m.start(1))
        breaks.append(m.end())
    return breaks


def find_kaoju_structure_breaks(prot: str) -> list[int]:
    """七国考结构断点：卷首、门类、词条+策/史记、X曰"、按礼。"""
    breaks: list[int] = []

    for m in VOL_HEAD_RE.finditer(prot):
        if m.start() > 0:
            breaks.append(m.start())
        breaks.append(m.end())

    for m in SECTION_HEAD_RE.finditer(prot):
        if m.start() > 0:
            breaks.append(m.start())
        breaks.append(m.end())

    for m in LEMMA_BEFORE_SRC_RE.finditer(prot):
        lemma = m.group(1)
        if not looks_like_lemma(lemma) and lemma not in ("相国", "左右丞相", "客卿"):
            # 相国 以 相 结尾，looks_like 应 True；再保险
            if lemma not in ("相国",):
                continue
        breaks.append(m.start(1))
        breaks.append(m.end(1))  # 词条后（策/史记 起）

    for m in SPEECH_OPEN_RE.finditer(prot):
        prev = prot[m.start() - 1] if m.start() > 0 else ""
        if not is_speech_open_worth_break(m.group(1), prev):
            continue
        if m.start() > 0:
            breaks.append(m.start())
    for m in SPEECH_CLOUD_RE.finditer(prot):
        if m.start() > 0:
            breaks.append(m.start())

    # 按礼：/ 按物原  — 含「秦按礼」把国名留前段
    for m in re.finditer(
        r"(?:^|[。！？；])((?:秦|楚|齐|燕|赵|魏|韩)?)(按(?:礼|周礼|物原)[：:]?)",
        prot,
    ):
        an_start = m.start(2)
        if an_start > 0:
            breaks.append(an_start)

    return breaks


def find_inline_breaks(prot: str, style: str = "chrono") -> list[int]:
    """在已 protect 的文本里插入断点。"""
    breaks: list[int] = []

    def rest_is_break(rest: str) -> bool:
        if not rest or rest.startswith("⟦A"):
            return False
        if style != "kaoju" and is_gz_year_mark_start(rest):
            return True
        if is_volume_start(rest):
            return True
        if is_an_start(rest):
            return True
        if is_source_colon_start(rest):
            return True
        if style == "kaoju":
            if is_you_start(rest):
                return True
            if is_speech_start(rest):
                return True
            if rest.startswith("钦定四库全书"):
                return True
            if re.match(
                r"^[秦楚齐燕赵魏韩](?:职官|食货|兵制|都邑|地理|田赋|官制|宫室)",
                rest,
            ):
                return True
            m = re.match(r"([\u4e00-\u9fff]{2,6})。", rest)
            if m and looks_like_lemma(m.group(1)):
                return True
            return False
        if rest.startswith(("是岁", "是年", "是春", "是夏", "是秋", "是冬", "是月")):
            return True
        if is_relative_year_start(rest):
            return True
        for era in ERA_NAMES:
            if rest.startswith(era):
                tail = rest[len(era) :]
                if re.match(YEAR_NUM + r"年", tail) or re.match(
                    YEAR_NUM + r"[春夏秋冬]", tail
                ):
                    return True
        for mon in MONTHS:
            if rest.startswith(mon):
                return True
        if len(rest) >= 2 and rest[:2] in GANZHI:
            return True
        return False

    for m in re.finditer(r"[。！？；」』\"']", prot):
        j = m.end()
        if rest_is_break(prot[j:]):
            breaks.append(j)

    # 】后紧接月份/季节/是岁/年号/干支标 → 强制断（…败绩。】十一月…）
    if style != "kaoju":
        for m in re.finditer(r"】", prot):
            rest = prot[m.end() :]
            if not rest:
                continue
            if rest_is_break(rest) or is_break_start(rest, style=style):
                breaks.append(m.end())
            # 保护 token 后：⟧ 也可能是注释结束
        for m in re.finditer(r"⟧", prot):
            rest = prot[m.end() :]
            if rest and (rest_is_break(rest) or is_break_start(rest, style=style)):
                breaks.append(m.end())

    # 句中/】后紧接【干支】年标也断（…从畧。】。【乙未】… / 异志。【甲午】）
    if style != "kaoju":
        for m in GZ_YEAR_MARK_RE.finditer(prot):
            if m.start() > 0:
                breaks.append(m.start())

    for j, end, matched in find_source_colon_spans(prot):
        if j == 0:
            continue
        prev = prot[j - 1]
        if prev == "⟧":
            continue
        if style == "kaoju":
            k = peel_lemma_before(prot, j)
            if k is not None and k < j:
                breaks.append(k)
            breaks.append(j)
        else:
            if prev not in "。！？；\n":
                breaks.append(j)

    if style == "kaoju":
        breaks.extend(find_lemma_sentence_breaks(prot))
        breaks.extend(find_kaoju_structure_breaks(prot))
        for m in re.finditer(r"又", prot):
            rest = prot[m.start() :]
            if not is_you_start(rest):
                continue
            if m.start() == 0:
                continue
            prev = prot[m.start() - 1]
            if prev in "。！？；，、」』\"'\n⟧" or prev.isascii():
                breaks.append(m.start())
            elif prev in "也矣焉耳乎哉":
                breaks.append(m.start())

    # 卷首（chrono/kaoju 通用）：…正文。钦定…卷二… → 在卷首前断
    breaks.extend(find_volume_breaks(prot))

    # 编年体：【甲午】年号干支标前断（与上列 rest 断互补，覆盖无句号粘连）
    if style != "kaoju":
        breaks.extend(find_gz_year_breaks(prot))

    return sorted(set(breaks))


def strip_volume_tails(text: str) -> str:
    """去掉卷末重复卷标，保留下一卷卷首。

    例：…始谋此。钦定重订大金国志卷一钦定四库全书钦定重订大金国志卷二纪年…
      → …始谋此。钦定四库全书钦定重订大金国志卷二纪年…
    """
    # OCR：大金国志春十四 → 大金国志卷十四
    text = re.sub(
        rf"(钦定重订大金国志)春({VOL_CN})",
        r"\1卷\2",
        text,
    )
    prev = None
    while prev != text:
        prev = text
        text = VOL_TAIL_BEFORE_NEXT_RE.sub("", text)
    return text


def peel_inline_time_breaks(paragraphs: list[str]) -> list[str]:
    """句号/】后的时间词另起段。

    典型：自动标点曾把「十一，月」切开，回粘成「十一月」后仍粘在上段末：
      …败绩。【按…】十一月，遣使…
    或：…无色也。夏取辽渤海军…

    注意：不得把岁标【丙申】与后文「收国二年…」切开。
    """
    mon = r"(?:闰)?(?:正|十[一二]?|[一二三四五六七八九])月"
    season = (
        r"(?:春(?!秋|申|水)|夏(?!人|国|商|后|月|水)|秋(?!山)|冬(?!夏))"
        r"(?:正月|二月|三月|四月|五月|六月|七月|八月|九月|十月|十一月|十二月|，|"
        r"取|遣|帝|诏|发|起|制|师|兵|大|复|左|右|宋|我|元)"
    )
    rel = r"(?:是岁|是年|次年|明年|翌年)"
    era = (
        r"(?:天会|天辅|天眷|皇统|天徳|天德|贞元|正隆|大定|明昌|承安|"
        r"泰和|大安|崇庆|至宁|贞祐|兴定|元光|正大|开兴|天兴|收国)"
        r"(?:元|[一二三四五六七八九十]+)年"
    )
    gz = rf"【{GZ_STEM}】"
    time_re = re.compile(rf"^(?:{rel}|{mon}|{season}|{era}|{gz})")

    out: list[str] = []
    # 卷首九帝年谱：每位皇帝整段，禁止按月/改元 peel
    in_nianpu = False
    for p in paragraphs:
        s = p.strip()
        if not s:
            continue
        if s.startswith("金九帝年谱"):
            in_nianpu = True
            out.append(s)
            continue
        if in_nianpu:
            if JUAN_YI_TITLE_RE.match(s) or (
                s.startswith("钦定") and "大金国志卷一" in s
            ):
                in_nianpu = False
            else:
                # 年谱区内整段保留（含帝条续段；后续 merge 会并回）
                out.append(s)
                continue
        # 已是整帝条（重跑场景）也不 peel
        if is_nianpu_emperor_start(s) and not s.startswith("金九帝起"):
            out.append(s)
            continue
        prot, tokens = protect_annots(s)
        cuts: list[int] = []
        for m in re.finditer(r"[。！？；】⟧]", prot):
            j = m.end()
            rest = prot[j:]
            if not rest or not time_re.match(rest):
                continue
            # 】后若是「【干支】」岁标本身的结束，且 rest 是年号正文 → 不切
            # 例：【丙申】收国二年…  的 】 后 rest=收国二年
            ch = prot[m.start()]
            if ch == "】":
                before = prot[: m.start() + 1]
                if re.search(rf"【{GZ_STEM}】$", before):
                    continue
            if ch == "⟧":
                # token 结束：仅当该 token 是注释（A）且后接时间；岁标不在 token 里
                # 若 rest 以【干支】起也不在此（岁标明文）
                pass
            cuts.append(j)
        if not cuts:
            out.append(s)
            continue
        last = 0
        for j in cuts:
            chunk = prot[last:j].strip()
            if chunk:
                out.append(restore_annots(chunk, tokens))
            last = j
        tail = prot[last:].strip()
        if tail:
            out.append(restore_annots(tail, tokens))
    return out


def drop_orphan_volume_tails(paragraphs: list[str]) -> list[str]:
    """删掉单独成段的卷末标（下一卷卷首另段保留）。"""
    out: list[str] = []
    for i, p in enumerate(paragraphs):
        s = p.strip()
        if VOL_TAIL_ONLY_RE.match(s):
            # 书末最后一段卷标也删
            nxt = paragraphs[i + 1].strip() if i + 1 < len(paragraphs) else ""
            if not nxt or is_volume_start(nxt):
                continue
        out.append(p)
    return out


def normalize_volume_heads(text: str) -> str:
    """卷首前尽量有可断边界：句号后的卷标保持；粘在正文中的卷标前插断点由 find 处理。"""
    text = re.sub(r"<史部[^>]*>", "", text)
    text = re.sub(
        rf"(钦定重订大金国志)春({VOL_CN})",
        r"\1卷\2",
        text,
    )
    return text


def is_volume_start(s: str) -> bool:
    """卷首起段：钦定四库全书钦定重订大金国志卷二… / 钦定重订大金国志卷二…"""
    s = s.strip()
    if not s:
        return False
    if VOL_START_RE.match(s):
        return True
    if s.startswith("钦定重订大金国志卷") or s.startswith("钦定四库全书钦定重订大金国志卷"):
        return True
    if s.startswith("钦定四库全书") and "卷" in s[:40]:
        return True
    return False


def is_volume_title_only(s: str) -> bool:
    """整段仅卷名：钦定…大金国志卷首 / 卷一"""
    s = s.strip()
    return bool(re.fullmatch(r"(?:钦定四库全书)?钦定重订大金国志(?:卷首|卷(?:首|[一二三四五六七八九]|十[一二三四五六七八九]?|二十[一二三四五六七八九]?|三十[一二三四五六七八九]?|四十[一]?))", s))


def find_volume_breaks(prot: str) -> list[int]:
    """在卷首处断段；卷名后正文再断一次。

    例：…始谋此。|钦定四库全书钦定重订大金国志卷二|纪年太祖…
        |钦定…卷首|大金初兴本末金国本名…
    """
    breaks: list[int] = []
    for m in VOL_START_RE.finditer(prot):
        if m.start() > 0:
            breaks.append(m.start())
        # 卷名结束后（卷首 / 卷N）再断，正文另段
        # VOL_START_RE 已匹配到 卷首 或 卷N 末
        end = m.end()
        if end < len(prot):
            # 卷首 特殊：匹配可能只到「卷」+「首」——VOL_CN 含「首」
            breaks.append(end)
    return breaks


def peel_volume_titles(paragraphs: list[str]) -> list[str]:
    """卷名单独成段：钦定…大金国志卷首 / 卷一 与后文拆开。"""
    out: list[str] = []
    for p in paragraphs:
        m = VOL_TITLE_ONLY_RE.match(p.strip())
        if not m:
            out.append(p)
            continue
        title, rest = m.group(1), m.group(2).strip()
        out.append(title)
        if rest:
            out.append(rest)
    return out


# 卷后「概括」：纪年太祖武元皇帝上 / 开国功臣传 / 文学翰苑上 …
VOL_SECTION_HEAD_RE = re.compile(
    r"^("
    r"纪年(?:"
    r"太祖武元皇帝[上下]"
    r"|太宗文烈皇帝[一二三四五六]"
    r"|大宗文烈皇帝[一二三四五六]"
    r"|[熈熙]宗孝成皇帝[一二三四]"
    r"|海陵.{0,3}王[上中下]"
    r"|海陵炀王[上中下]"
    r"|世宗圣明皇帝[上中下]"
    r"|章宗皇帝[上中下]"
    r"|东海郡侯[上下]"
    r"|宣宗皇帝[上下]"
    r"|义宗皇帝"
    r")"
    r"|开国功臣传"
    r"|文学翰苑[上下]"
    r"|楚国张邦昌录"
    r"|齐国刘豫录"
    r"|立楚国张邦昌册文"
    r"|立楚齐国册文"
    r"|天文"
    r"|旗帜"
    r"|杂色仪制"
    r"|皂."  # 皂隶 / 坏字一字符
    r"|两国往来誓书|两国徃来誓书"
    r"|京府州军"
    r"|初兴风土"
    r"|许奉使行程录"
    r"|译改国语解"
    r")(.*)$"
)


def peel_volume_section_heads(paragraphs: list[str]) -> list[str]:
    """卷名后的概括单独成段。

    例：纪年太祖武元皇帝上太祖武元皇帝，元名…
      → 纪年太祖武元皇帝上
         太祖武元皇帝，元名…
    """
    out: list[str] = []
    for p in paragraphs:
        s = p.strip()
        m = VOL_SECTION_HEAD_RE.match(s)
        if not m:
            out.append(p)
            continue
        head, rest = m.group(1), (m.group(2) or "").strip()
        head = head.rstrip("。．.、，,")
        out.append(head)
        if rest:
            rest = re.sub(r"^[。．.]+", "", rest).strip()
            if rest:
                out.append(rest)
    return out




# 卷首两篇：大金初兴本末 / 金九帝年谱（目录：卷首大金初兴本末金九帝年谱）
JUAN_SHOU_TITLE_RE = re.compile(
    rf"^(?:钦定四库全书)?钦定重订大金国志卷首$"
)
JUAN_YI_TITLE_RE = re.compile(
    rf"^(?:钦定四库全书)?钦定重订大金国志卷一$"
)

def split_dajin_juan_shou_body(blob: str) -> list[str]:
    """卷首正文：大金初兴本末 + 金九帝年谱 + 各帝 + 总年。"""
    blob = re.sub(r"\s+", "", blob)
    # 帝号误断：海陵，炀王 → 海陵炀王
    blob = blob.replace("海陵，炀王", "海陵炀王").replace("海陵,炀王", "海陵炀王")
    blob = re.sub(rf"钦定重订大金国志卷首$", "", blob)
    out: list[str] = []

    if blob.startswith("大金初兴本末"):
        out.append("大金初兴本末")
        blob = blob[len("大金初兴本末") :]

    m = re.search(r"金九帝年谱：?", blob)
    if m:
        chuxing = blob[: m.start()].strip()
        if chuxing:
            out.append(chuxing)
        out.append("金九帝年谱：")
        rest = blob[m.end() :]
    else:
        if blob.strip():
            out.append(blob.strip())
        return out

    # 条目标题：后接【 才切（注解内「降帝为东海郡侯。」后无【，不切）
    EMP = re.compile(
        r"(太祖武元皇帝【"
        r"|太宗文烈皇帝【"
        r"|[熈熙]宗孝成皇帝【"
        r"|海陵炀王【|海陵，炀王【"
        r"|世宗圣明皇帝【"
        r"|章宗皇帝【"
        r"|东海郡侯【"
        r"|宣宗皇帝【"
        r"|义宗皇帝【"
        r"|金九帝起)"
    )
    cuts = [0]
    for m2 in EMP.finditer(rest):
        if m2.start() > 0:
            cuts.append(m2.start())
    cuts.append(len(rest))

    for a, b in zip(cuts, cuts[1:]):
        piece = rest[a:b].strip()
        if piece:
            out.append(piece)

    fixed: list[str] = []
    i = 0
    while i < len(out):
        p = out[i]
        if p.startswith("金九帝起") and i + 1 < len(out):
            nxt = out[i + 1]
            if "一百二十" in nxt or nxt.startswith("甲午"):
                p = p + nxt
                i += 1
        fixed.append(p)
        i += 1
    return [x for x in fixed if x]


def restructure_dajin_juan_shou(paragraphs: list[str]) -> list[str]:
    """在段列表里定位 卷首→卷一，重切卷首两篇。"""
    i0 = None
    i1 = None
    for i, p in enumerate(paragraphs):
        s = p.strip()
        if JUAN_SHOU_TITLE_RE.match(s) and i0 is None:
            i0 = i
        if JUAN_YI_TITLE_RE.match(s):
            i1 = i
            break
    if i0 is None or i1 is None or i1 <= i0 + 1:
        return paragraphs
    mid = paragraphs[i0 + 1 : i1]
    blob = "".join(mid)
    if "大金初兴本末" not in blob and "金九帝" not in blob:
        return paragraphs
    new_mid = split_dajin_juan_shou_body(blob)
    return paragraphs[: i0 + 1] + new_mid + paragraphs[i1:]


# 金九帝年谱：每位皇帝整段（禁止按月/年号 peel 拆碎）
NIANPU_EMP_START_RE = re.compile(
    r"^(?:"
    r"太祖武元皇帝【|"
    r"太宗文烈皇帝【|"
    r"[熈熙]宗孝成皇帝【|"
    r"海陵炀王【|海陵，炀王【|"
    r"世宗圣明皇帝【|"
    r"章宗皇帝【|"
    r"东海郡侯【|"
    r"宣宗皇帝【|"
    r"义宗皇帝【|"
    r"金九帝起"
    r")"
)


def is_nianpu_emperor_start(s: str) -> bool:
    s = (s or "").strip()
    return bool(s) and bool(NIANPU_EMP_START_RE.match(s))


def merge_dajin_nianpu_emperor_blocks(paragraphs: list[str]) -> list[str]:
    """卷首《金九帝年谱》特殊：每位皇帝整块，不按月份/改元拆段。

    用户铁律：卷首年谱不是正文编年；不得被 peel_inline_time_breaks / soft_wrap 拆碎。
    """
    i_title = None
    i_juan1 = None
    for i, p in enumerate(paragraphs):
        s = p.strip()
        if i_title is None and (s.startswith("金九帝年谱") or s == "金九帝年谱："):
            i_title = i
        if JUAN_YI_TITLE_RE.match(s):
            i_juan1 = i
            break
    if i_title is None:
        return paragraphs
    end = i_juan1 if i_juan1 is not None else len(paragraphs)
    if end <= i_title + 1:
        return paragraphs

    head = paragraphs[: i_title + 1]
    mid = paragraphs[i_title + 1 : end]
    tail = paragraphs[end:]

    # 只合并「帝号【…」到下一帝/总年 之间的碎片
    merged: list[str] = []
    buf = ""
    for p in mid:
        s = p.strip()
        if not s:
            continue
        if is_nianpu_emperor_start(s):
            if buf:
                merged.append(buf)
            buf = s
        else:
            # 标题后、帝号前的碎段（极少）或帝条被 peel 出的续段
            if buf:
                buf += s
            else:
                # 尚无帝条：若是本末残留不应到这里；保守保留
                merged.append(s)
    if buf:
        merged.append(buf)

    # 金九帝起 后若误粘下一卷，不处理（end 已卡在卷一）
    return head + merged + tail


def skip_peel_for_nianpu(paragraphs: list[str]) -> list[str]:
    """标记用：实际逻辑在 peel 外包一层 — 见 peel_inline_time_breaks_safe。"""
    return paragraphs






def strip_false_quote_closes(text: str) -> str:
    """去掉 云" 后误收的短引号，且后文仍是同一句续文。

    例：云"册文骂我"我都… → 云"册文骂我我都…
    只删多余收尾，绝不补新引号。
    注意：不处理 曰"——对话嵌套多，易误伤 淮南子曰" 等开引。
    """
    pat = re.compile(
        r'(云)"([^"\n。！？]{1,20})"([\u4e00-\u9fff，、；：])'
    )

    def repl(m: re.Match) -> str:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        return f'{head}"{body}{tail}'

    prev = None
    while prev != text:
        prev = text
        text = pat.sub(repl, text)
    return text


def soft_wrap(p: str, soft_max: int) -> list[str]:
    # 金九帝年谱帝条：整段不切
    if is_nianpu_emperor_start(p.strip()):
        return [p]
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


def merge_orphan_short(paras: list[str]) -> list[str]:
    """合并误切单字段；「又」「按」单字并入下一段；残留国名并入上段。"""
    out: list[str] = []
    i = 0
    while i < len(paras):
        p = paras[i]
        if len(p) == 1 and p not in ANNOT_CHARS:
            if p in ("又", "按") and i + 1 < len(paras):
                paras[i + 1] = p + paras[i + 1]
                i += 1
                continue
            if out and not is_source_colon_start(p):
                out[-1] += p
                i += 1
                continue
        # 单独国名 且下段 按… → 并上
        if re.fullmatch(r"[秦楚齐燕赵魏韩]", p) and out:
            if i + 1 < len(paras) and paras[i + 1].startswith("按"):
                out[-1] += p
                i += 1
                continue
            out[-1] += p
            i += 1
            continue
        # 段末带残留国名：「乐池相。秦」
        if out is not None and re.search(r"[。！？]([秦楚齐燕赵魏韩])$", p):
            # 若下一段是按，国名应在本段（正确）；不处理
            pass
        out.append(p)
        i += 1
    # 二次：…相。秦 + 按礼 → …相秦。 + 按礼（国名并入句末，符合用户样例「乐池相秦。」）
    fixed2: list[str] = []
    j = 0
    while j < len(out):
        p = out[j]
        if (
            j + 1 < len(out)
            and out[j + 1].startswith("按")
            and re.search(r"([。！？])([秦楚齐燕赵魏韩])$", p)
        ):
            p = re.sub(r"([。！？])([秦楚齐燕赵魏韩])$", r"\2\1", p)
            fixed2.append(p)
            j += 1
            continue
        fixed2.append(p)
        j += 1
    return fixed2


def resegment(raw: str, soft_max: int = 1000, style: str = "chrono") -> str:
    raw = strip_wiki_chrome(raw)
    # 只删误收短引号，绝不补新 "
    raw = strip_false_quote_closes(raw)
    # 卷尾重复卷标删除，保留下一卷卷首
    raw = strip_volume_tails(raw)
    raw = normalize_volume_heads(raw)
    # 【丙申】。收国二年 → 【丙申】收国二年（去掉误点/跨行）
    if style != "kaoju":
        raw = normalize_gz_year_marks(raw)
    # 大金国志开卷目录粘连 → 按卷分行
    raw = expand_dajin_toc_front(raw)
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

    # 已展开的目录行：空行分段，勿再拼成 blob 抹掉
    # 策略：对「纯目录短行」保留为独立段，其余再合并后 find_inline_breaks
    pre_paras: list[str] = []
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        if buf:
            pre_paras.append("".join(buf))
            buf = []

    for line in body:
        st = line.strip()
        if not st:
            flush_buf()
            continue
        # 目录行 / 史部 / 目录题 / 卷N… / 提要头 / 乾隆恭校
        is_toc_line = bool(
            re.match(r"^钦定四库全书史部", st)
            or re.match(r"^钦定重订大金国志目录", st)
            or re.match(rf"^卷{VOL_CN}", st)
            or st.startswith("卷首")
            or st.startswith(DAJIN_TIYAO_MARK)
            or st.startswith("【臣】等谨案")
            or re.match(r"^乾隆\d+年", st)
        )
        if is_toc_line:
            flush_buf()
            pre_paras.append(st)
        else:
            # 年号干支标另起段；其它【】注释并回上句
            if (
                style != "kaoju"
                and is_gz_year_mark_start(st)
            ):
                flush_buf()
                buf.append(st)
            elif buf and st and st[0] in ANNOT_CHARS and not is_gz_year_mark_start(st):
                buf[-1] += st
            else:
                buf.append(st)
    flush_buf()

    # 对非目录段做 protect + inline breaks；目录段原样保留
    paragraphs: list[str] = []
    for block in pre_paras:
        st = block.strip()
        if not st:
            continue
        is_toc_line = bool(
            re.match(r"^钦定四库全书史部", st)
            or re.match(r"^钦定重订大金国志目录", st)
            or re.match(rf"^卷{VOL_CN}", st)
            or st.startswith("卷首")
            or st.startswith(DAJIN_TIYAO_MARK)
            or st.startswith("【臣】等谨案")
            or re.match(r"^乾隆\d+年", st)
        )
        if is_toc_line:
            paragraphs.append(st)
            continue

        prot, tokens = protect_annots(st)
        cuts = set(find_inline_breaks(prot, style=style))
        pieces: list[str] = []
        last = 0
        sentence_ends = [m.end() for m in re.finditer(r"[。！？]", prot)]
        markers = sorted(set(list(cuts) + sentence_ends + [len(prot)]))
        for end in markers:
            if end <= last:
                continue
            chunk = prot[last:end]
            if chunk.strip():
                pieces.append(restore_annots(chunk.strip(), tokens))
            if end in cuts:
                pieces.append("§BR§")
            last = end

        cur: list[str] = []
        for s in pieces:
            if s == "§BR§":
                if cur:
                    paragraphs.append("".join(cur))
                    cur = []
                continue
            if is_break_start(s, style=style) and cur:
                paragraphs.append("".join(cur))
                cur = [s]
            else:
                cur.append(s)
        if cur:
            paragraphs.append("".join(cur))

    if style == "kaoju":
        paragraphs = merge_orphan_short(paragraphs)
        paragraphs = [
            re.sub(r"^策(?![：:])([\u4e00-\u9fff])", r"策：\1", p)
            if p.startswith("策") and not p.startswith("策：") and not p.startswith("策书")
            else p
            for p in paragraphs
        ]

    # 删单独卷末标段
    paragraphs = drop_orphan_volume_tails(paragraphs)
    # 卷名与正文拆开
    paragraphs = peel_volume_titles(paragraphs)
    # 卷后概括（纪年××上 / 开国功臣传…）单独成段
    paragraphs = peel_volume_section_heads(paragraphs)
    # 卷首：大金初兴本末 / 金九帝年谱 / 各帝
    paragraphs = restructure_dajin_juan_shou(paragraphs)
    paragraphs = merge_dajin_nianpu_emperor_blocks(paragraphs)
    # 再 peel 一次：卷首重构后 / soft 前 仍可能粘连
    paragraphs = peel_volume_section_heads(paragraphs)
    # 孤立【丙申】。+ 下年事 → 并成一段
    if style != "kaoju":
        paragraphs = merge_lonely_gz_year_marks(paragraphs)
        # 】/。后 十一月/夏取/是岁… 另起段（回粘月份后常见粘连）
        paragraphs = peel_inline_time_breaks(paragraphs)

    final: list[str] = []
    for p in paragraphs:
        # 目录短行不做 soft_wrap 合并
        is_toc_line = bool(
            re.match(r"^钦定四库全书史部", p)
            or re.match(r"^钦定重订大金国志目录", p)
            or re.match(rf"^卷{VOL_CN}", p)
            or p.startswith("卷首")
            or p.startswith(DAJIN_TIYAO_MARK)
            or p.startswith("【臣】等谨案")
            or re.match(r"^乾隆\d+年", p)
        )
        if is_toc_line:
            final.append(p.strip())
            continue
        for piece in soft_wrap(p, soft_max):
            piece = piece.strip()
            if not piece:
                continue
            # 年号干支标起首 → 独立段；其它【】注释并回上段
            if final and piece[0] in ANNOT_CHARS and not is_gz_year_mark_start(piece):
                final[-1] += piece
            else:
                final.append(piece)

    # 仅清理段首真注释【按…】/【臣】，不要删【甲午】年标
    if final and final[0] and final[0][0] in ANNOT_CHARS and not is_gz_year_mark_start(final[0]):
        final[0] = re.sub(r"^【[^】]{0,80}】", "", final[0]).lstrip()
        if not final[0]:
            final = final[1:]
        elif final[0][0] in ANNOT_CHARS and not is_gz_year_mark_start(final[0]) and len(final) > 1:
            final[1] = final[0] + final[1]
            final = final[1:]

    # 再扫一遍：孤立【干支】仍可能出现在 soft_wrap 后
    if style != "kaoju":
        final = merge_lonely_gz_year_marks(final)
        final = peel_inline_time_breaks(final)
        final = merge_lonely_gz_year_marks(final)
        final = merge_dajin_nianpu_emperor_blocks(final)

    out_parts = []
    if headers:
        out_parts.append("\n".join(headers))
    out_parts.append("\n\n".join(final))
    return "\n\n".join(out_parts).strip() + "\n"


def check(name: str, text: str, style: str = "chrono"):
    paras = [p for p in text.split("\n\n") if p.strip() and not p.startswith("（")]
    # 段首【按…】/【臣】禁；【干支】年标允许
    bad_p = sum(
        1
        for p in paras
        if p and p[0] in ANNOT_CHARS and not is_gz_year_mark_start(p)
    )
    lines = [l for l in text.splitlines() if l.strip() and not l.startswith("（")]
    bad_l = sum(
        1
        for l in lines
        if l and l[0] in ANNOT_CHARS and not is_gz_year_mark_start(l)
    )
    lens = [len(p) for p in paras] or [0]
    print(
        f"{name} [{style}]: n={len(paras)} bad_p={bad_p} bad_l={bad_l} "
        f"max={max(lens)} avg={sum(lens)//len(lens)}"
    )
    terms = [
        "史记：",
        "李斯传：",
        "按",
        "余按",
        "又",
        "右尹",
        "卫尉",
        "是岁",
        "是年",
        "次年",
        "明年",
        "十二月",
        "三月",
        "八月",
        "【甲",
        "【乙",
        "【丙",
        "【丁",
    ]
    for term in terms:
        c = sum(1 for p in paras if p.startswith(term))
        if c:
            print(f"  段首{term}:{c}")
    lonely = sum(1 for p in paras if GZ_YEAR_MARK_LONELY_RE.match(p.strip()))
    if lonely:
        print(f"  lonely【干支】:{lonely}")
        for p in paras:
            if GZ_YEAR_MARK_LONELY_RE.match(p.strip()):
                print("   ", p[:40])
                break
    if bad_p:
        for p in paras:
            if p and p[0] in ANNOT_CHARS and not is_gz_year_mark_start(p):
                print("  BAD PARA:", p[:120])
                break
    return bad_p, bad_l


def main():
    # usage: resegment_annots.py [--style kaoju|chrono] [files...]
    args = sys.argv[1:]
    style = "chrono"
    files: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
            continue
        files.append(args[i])
        i += 1
    if not files:
        files = ["/root/projects/text-search/data/先秦/七国考.txt"]
        style = "kaoju"

    for path in files:
        dest = Path(path)
        # 七国考默认 kaoju
        st = style
        if "七国考" in dest.name and style == "chrono" and "--style" not in sys.argv:
            st = "kaoju"
        if "七国考" in dest.name:
            st = "kaoju"
        raw = dest.read_text(encoding="utf-8")
        fixed = resegment(raw, soft_max=1200 if st == "kaoju" else 1000, style=st)
        dest.write_text(fixed, encoding="utf-8")
        check(dest.name, fixed, style=st)
        if "七国" in dest.name:
            t = fixed
            for key in ["廷尉。", "都尉。", "右尹", "李斯传：", "按尚书"]:
                i0 = t.find(key)
                if i0 >= 0:
                    pre = t[max(0, i0 - 4) : i0]
                    print(
                        f"  sample {key}: pre={pre!r} | "
                        f"{t[i0:i0+55].replace(chr(10), ' ↵ ')}"
                    )
        if "大金" in dest.name:
            t = fixed
            for key in ["次年三月", "册文骂我", "十二月，使至杨朴"]:
                i0 = t.find(key)
                if i0 >= 0:
                    pre = t[max(0, i0 - 6) : i0]
                    print(
                        f"  sample {key}: pre={pre!r} | "
                        f"{t[i0:i0+70].replace(chr(10), ' ↵ ')}"
                    )


if __name__ == "__main__":
    main()