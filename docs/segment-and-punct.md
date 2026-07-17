# 史料分段与断句定稿

> 与 Hermes skill `historical-text-segment-and-punct` 同步。  
> 实现脚本：`scripts/normalize_variants.py` · `scripts/resegment_annots.py` · `scripts/repair_false_punct.py`  
> 更细算法与验收 assert 见仓库外 skill 引用：`liaosong-variant-and-resegment` / `siku-volume-resegment` / `auto-punct-false-split-repair` / `kaoju-qiguokao-resegment`。

**状态说明（2026-07-17 夜）**：用户要求暂停继续改《大金国志》正文，先沉淀规则。当前活跃本已部分应用规则，但 **句内断句仍不理想**（auto-punct 底噪高）；规则修复 ≠ 全书精校。

---

## 1. 总流水线（顺序不可乱）

```text
原料 / auto_punct
  → opencc t2s
  → normalize_variants.py      # 异体
  → resegment_annots.py        # 分段（kaoju | chrono）
  → repair_false_punct.py      # 句内专名/年月回粘
  → 抽查验收
```

```bash
cd /path/to/text-search

python3 scripts/normalize_variants.py
python3 scripts/resegment_annots.py data/辽宋金夏/大金国志.txt --style chrono
python3 scripts/repair_false_punct.py \
  --active data/辽宋金夏/大金国志.txt \
  --raw data/_raw_no_punct/大金国志.txt
```

| 层 | 脚本 | 职责 |
|----|------|------|
| 字形 | `normalize_variants.py` | 扩展区 + 日新字体 + 旧字形（如 㑹→会、増→增、髙→高、宻→密、熈→熙） |
| 段 | `resegment_annots.py` | 卷层/目录/卷首/年季干支/`【干支】`/注释保护/年谱整帝 |
| 句内 | `repair_false_punct.py` | 专名中间误断、年月误断、高置信语义逗号 |
| 模型 | `auto_punctuate.py` | 只负责加标点；**不要**重跑模型修专名切分 |

---

## 2. 分段规则

### 2.1 公共

1. 保护注释块 `【…】` / `〈…〉`，注释内句号不切段。
2. **禁止**段首为 `【按…】` / `【臣】` / 残 `】`（并回上段）。
3. **例外**：纯 **`【干支】` 岁标**（`【甲午】`…）**必须另起段**；禁止孤立 `【丙申】。` 再下段写年事 → 并成 `【丙申】收国二年…`。
4. **禁止** AI 猜补收尾引号；仅允许删除 `云"短"续` 类误收短闭引（只匹配「云」）。
5. auto-punct 常「一句一行」→ 按规则**组段**，不是每行一段。

### 2.2 `chrono`（编年 / 会编 / 要录 / 大金国志）

可断段首：

- 年号年：`天会四年` / `建炎元年` / `绍兴十年`…
- 季节（可带月）：`春正月` / `夏` / `秋` / `冬`
- 相对年：`是岁` / `是年` / `次年` / `明年` / `翌年`（含 `次年三月`）
- 干支日、引书句式
- **`【干支】` 岁标**
- **句中时间 peel**（`peel_inline_time_breaks`）：在 `。！？；` / `】` 后若接月份、季节起事、是岁、年号年、`【干支】` → 强制另起  
  - **保护**：不切开 `【丙申】收国二年…`

### 2.3 `kaoju`（七国考等）

| 要 | 不要 |
|----|------|
| 门类、词条单独段 | 年号/季节/干支断（那是 chrono） |
| `策：`（战国策简写）、`史记：` / `X传：` / `通鉴：` | 把 `相国策` 整吞为 `国策` |
| `按` / `余按` / `又…` 起段 | 按礼内职级罗列切成伪词条 |

开卷权威结构示例：

```text
钦定四库全书七国攷卷一明董说撰。
秦职官〈封君后妃附〉
相国
策：卫鞅亡，入秦孝公以为相。
史记：…乐池相秦。
按礼：…
```

### 2.4 四库卷次（大金国志）

每卷三层，**各自单独段**：

1. 卷名：`钦定四库全书钦定重订大金国志卷一`
2. 概括：`纪年太祖武元皇帝上` / `开国功臣传` / `文学翰苑上`…
3. 正文：起传、年事；岁次 `【辛丑】天辅五年春…`

另：开卷目录每行一卷；提要整段；删卷尾重复卷标；**卷号长优先**（禁「卷三十七」→「卷三」）。

全本门控：plain 汉字量约 **≥14–15 万**、卷首～卷四十一，才可当全本入库（~135KB 级为残本）。

### 2.5 🔴 卷首《金九帝年谱》特殊

**年谱 ≠ 正文编年。**

- 每位皇帝 **一整段**（从 `太祖武元皇帝【` 到下一帝号前）
- **禁止** 用正文时间 peel / soft_wrap 按月、改元拆碎
- 实现：`split_dajin_juan_shou_body` + `merge_dajin_nianpu_emperor_blocks`；peel 在「金九帝年谱」→「卷一」整区跳过
- 帝号：`海陵，炀王` → **`海陵炀王`**
- 验收：标题 + 9 帝 + `金九帝起` ≈ 11 段；orphan 月首 = 0  
- **任何**改写大金国志的流水线结束必须抽查卷首年谱

---

## 3. 断句规则（句内，repair）

### 3.1 铁律

1. **不要**重跑 guwen-biaodian 指望专名变好。
2. **禁止**「凡 raw 二字连写就删中间句号」——会吃合法句界（`死领`、丢 `东平，元帅府` 逗号）。
3. 词表用**简体**目标字（先 variants）。
4. **resegment 之后**再 repair。

### 3.2 典型

| 烂 | 应 |
|----|----|
| `东。平` / `元帅，府` | `东平` / `元帅府`；语义 `归至东平，元帅府` |
| `天会四，年` / `六，月` | `天会四年` / `六月` |
| `父，忧` / `侵，淮` | `父忧` / `侵淮` |
| `海陵，炀王` | `海陵炀王` |

`repair_false_punct.py`：`HARD_FIXES` → compounds → raw 词库 → 日期 → semantic_commas → 注释内 → 末轮。

用户锚句应贴近：

`归至东平，元帅府…知东平。六月，行下…死。领…侵淮，从之…取磁单等州`

---

## 4. 最低验收

```text
□ 段首非注释【按/臣】；【干支】岁标可
□ lonely 【干支】。 == 0
□ 东。平 / 云。中 / 天。祚 / N，月 == 0（repair 后）
□ 大金：【甲午】【乙未】【丙申】收国二年… 段首
□ 大金：卷首年谱结构 + 海陵炀王无逗号
□ 七国考：门类/词条/策：/史记：/按
□ 不声称「全书精校完成」
```

---

## 5. 相关脚本一览

| 脚本 | 作用 |
|------|------|
| [`scripts/normalize_variants.py`](../scripts/normalize_variants.py) | 全库/单文件异体 |
| [`scripts/resegment_annots.py`](../scripts/resegment_annots.py) | 语义分段 |
| [`scripts/repair_false_punct.py`](../scripts/repair_false_punct.py) | 专名/年月误断 |
| [`scripts/auto_punctuate.py`](../scripts/auto_punctuate.py) | 模型自动标点 |
| [`scripts/ingest_dajin_full_after_punct.py`](../scripts/ingest_dajin_full_after_punct.py) | 大金全本标点后入库管线 |

原料无标点全本应保留：`data/_raw_no_punct/大金国志.txt`（禁止被标点路径覆盖）。
