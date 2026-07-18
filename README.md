# 📚 史料检索（text-search）

[![Python 3](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://docs.python.org/3/library/http.server.html) | 零依赖 | 移动端可用

**零依赖、可自托管的中国古典/史料全文检索 Web 应用。**  
后端纯 Python 标准库（`http.server`），前端单页 HTML 无框架，数据为 `data/<时期>/<书名>.txt` 扁平文件。  
手机 / 桌面均可使用；**史料时代排序**、**书级勾选**、**OR/AND 检索**、**全文阅读器**。


---

---

## 🚀 快速开始

```bash
cd /path/to/text-search
python3 -u server.py 8899
# 浏览器 → http://127.0.0.1:8899
```

查询语法：

| 输入 | 含义 | 示例 |
|------|------|------|
| `兀术 乌珠` | **AND**：同时包含（空格） | `兀术 金史` |
| `兀术/乌珠` | **OR**：任一词 | `兀术/乌珠/宗弼` |
| `无恤+伯鲁` | **AND**：同一行同时包含 | `无恤+伯鲁` |
| 混合 | 组间 AND / 组内 OR | `兀术/乌珠+宗弼 金史` |

---

## ✨ 功能一览

| 类别 | 功能 | 说明 |
|------|------|------|
| 🔍 **检索** | 全文检索 | 逐行扫描 `data/` 下活跃 `.txt`；`/` = OR，`+` / 空格 = AND |
| | 书名检索 | 只搜书名 / 标签 / 作者 / 时代，一书一卡 |
| | 书级筛选 | 「筛选范围」内按书勾选；`books=时期/书名,...` |
| | 分页加载 | 真实 `total` + `returned` + `has_more` + **加载更多** |
| 🧭 **排序** | 史料时代排序 | `ERA_ORDER` 定序（春秋→战国→…→西汉→…→元→明→清） |
| | 同书行号排序 | 命中按正文先后顺序 |
| 📄 **展示** | 书组收起/展开 | 单书 **收起本书** 或 **展开 N 条**；顶栏 **收起全部书 / 展开全部书** |
| | 命中预览 | 默认只显示命中行整段；可展开前后文 |
| | 标签展示 | `书名·[时代]·作者`（来自 `books_meta.json`）；**时代按原书撰写朝代** |
| | 时期筛选 | 固定芯片：先秦 / 秦汉 / 魏晋南北朝 / 隋唐五代 / **辽宋夏金** / **蒙元** / 明 / 清（**无民国**） |
| 📖 **阅读器** | 打开定位 / 阅读全书 | 任意命中→「打开定位」跳转行、书组头「阅读全书」 |
| | 字号 A± / 行跳转 / 进度条 | 大书按约 400 行窗口分段加载 |
| | **在本书中检索** | 同一套 `/` `+` 语法；上一处/下一处按 OR 感知 terms |
| 🛠 **语料治理** | 异体字映射 | `normalize_variants.py`：扩展区+日新字体+旧字形（㑹→会、増→增、髙→高、宻→密、熈→熙） |
| | 语义分段 | `resegment_annots.py`：`chrono`/`kaoju`；注释保护；`【干支】` 岁标；四库卷三层 |
| | 卷首年谱特殊 | 大金国志九帝年谱：每位皇帝整段，禁按月拆（[docs](docs/segment-and-punct.md)） |
| | 专名误断修复 | `repair_false_punct.py` 词表+raw 回粘；禁全局删句号 |
| | 简体+有标点门控 | 活跃库必须简体有标点；原料放 `_raw_no_punct/` 隔离 |
| | 自动标点队列 | CPU 模型加标点后入库；**不指望重跑模型修好专名切分** |

---

## 📊 语料统计

| 时期目录 | 活跃书数 | 代表性书籍 | 原始字节 |
|----------|----------|-----------|----------|
| **先秦** | 70 部 | 史记、资治通鉴、春秋左传、论语、孟子、韩非子、庄子、楚辞、尚书、绎史、路史…… | ~41 MB |
| **秦汉** | 0（占位） | — | — |
| **魏晋南北朝** | 0（占位） | — | — |
| **隋唐五代** | 0（占位） | — | — |
| **辽宋夏金** | 14 部 | 宋史、辽史、金史、三朝北盟会编、建炎以来系年要录、续资治通鉴长编（及拾补）、大金国志、契丹国志…… | ~53 MB |
| **蒙元** | 8 部 | 元史、新元史、元朝秘史、圣武亲征录、蒙鞑备录、黑鞑事略、蒙古源流、长春真人西游记 | ~12 MB |
| **明** | 0（占位） | — | — |
| **清** | 0（占位） | — | — |
| **隔离区** | `_raw_no_punct/*.txt`（已入库公版原料） | 蒙元原料、大金国志、东都事略、宋史纪事本末、七国考、路史、绎史…… | ~34 MB |
| **总计（活跃）** | **92 部** | 简体+有标点 | **~105 MB** |

> 完整书单见 [`data/books_meta.json`](data/books_meta.json)（约 117 条 meta）。  
> 公开仓**仅收录公版 / 开放许可文本**；非公版现代整理本不入库、不进 Git。  
> 目录时期旧名：`辽宋金夏`→`辽宋夏金`，`元`→`蒙元`；筛选芯片已去掉 **民国**（meta 里「民国」仍可作单书时代标签，如《新元史》《清史稿》）。

---

## 📋 史料入库流程

```
开放源下载 / 公版文本
       │
       ▼
┌─────────────────────────────┐
│ 1. 入库前检查（每书必做）    │
├─────────────────────────────┤
│ □ 文字 → opencc t2s 简体   │
│ □ 标点 → 密度门控（。≥ 50）│
│ □ 编码 → UTF-8（含 GB18030 │
│   探测兜底）                │
│ □ 异字 → 扩展区+日新字体   │
│   映射表                    │
│ □ 卷帙 → 检查双卷标之间    │
│   是否有内容（防假完本）    │
│ □ 许可 → 仅公版/开放许可   │
│   （非公版不入库、不进仓）  │
└─────────────────────────────┘
       │ 通过? → 3
       │
       ▼
┌─────────────────────────────┐
│ 2. 隔离区 (_raw_no_punct/)  │
│    原料无标点/繁体保留      │
│    （可加入自动标点队列，    │
│     完成后→步骤3）          │
└─────────────────────────────┘
       │ 标点完成
       ▼
┌─────────────────────────────┐
│ 3. 入库                     │
│    data/<时期>/<书名>.txt   │
│    books_meta.json 更新     │
│    (era / author / label)   │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ 4. 验证                     │
│ □ 文件名仅「书名.txt」      │
│   （不含·[时代]·作者）       │
│ □ 无繁体同名文件（防双份）  │
│ □ meta 按时期目录放好       │
│   （用户可能要求史记放先秦） │
│ □ era 按原书撰写朝代        │
│   译注本：作者=原作者·译注  │
│ □ 搜索抽查（如「完颜亮」）  │
└─────────────────────────────┘
```

### 标点后治理（分段 / 断句）— 定稿

> 完整规则与验收清单：**[docs/segment-and-punct.md](docs/segment-and-punct.md)**  
> 对应脚本：`normalize_variants.py` → `resegment_annots.py` → `repair_false_punct.py`

```
auto_punct / 用户有标点本
       │
       ▼
  opencc t2s（繁→简）
       │
       ▼
  normalize_variants.py     # 异体全库或单书
       │
       ▼
  resegment_annots.py       # --style chrono | kaoju
  · chrono：年号/季节/次年/【干支】/句中时间 peel
  · kaoju：词条、策：/史记：、按（七国考）
  · 四库：卷名 ‖ 纪年概括 ‖ 正文
  · 卷首《金九帝年谱》：每位皇帝整段（≠正文编年）
       │
       ▼
  repair_false_punct.py     # 专名/年月句内回粘（需 _raw_no_punct 底本）
       │
       ▼
  抽查验收（干支/年谱/东。平等残量）
```

| 体例 | style | 代表书 |
|------|-------|--------|
| 编年 / 会编 / 国志纪年 | `chrono` | 大金国志、三朝北盟会编、建炎以来系年要录 |
| 考据 / 名词解释 | `kaoju` | 七国考 |

**铁律摘要：**

1. 分段与句内误断是两层问题；**不要**重跑模型指望专名变好。  
2. **禁止**「raw 二字连写就删中间句号」的全局对齐。  
3. 卷首九帝年谱 **禁止**按月份/改元拆段。  
4. `海陵，炀王` → **海陵炀王**；`海陵，炀主` → **海陵炀主**（**只去逗号，不改字**）。  
5. 断句完整规则见 [docs/segment-and-punct.md §3](docs/segment-and-punct.md)。  
6. 规则修复 **≠** 全书精校。  
### 异体字映射表

> **完整词库（79 单字 + 多字）与原则/验收**：[`docs/variant-map.md`](docs/variant-map.md)  
> 脚本：[`scripts/normalize_variants.py`](scripts/normalize_variants.py)（全活跃库一键；`--dry-run` 可统计）

| 类别 | 例（异体 → 简体） | 说明 |
|------|-------------------|------|
| **CJK 扩展区** | 㑹→会 㸃→点 㡬→几 䟽→疏 䧟→陷 㮚→栗 䝉→蒙 䕶→护 㓂→寇 㕘→参 𥳑→简 𫉬→获 | t2s 扫不到 |
| **日文新字体** | 増→增 乗→乘 従→从 毎→每 収→收 両→两 児→儿 焼→烧 抜→拔 挿→插 説→说 録→录 舎→舍 暦→历 覧→览 郷→乡 総→总 | 翻刻/库 |
| **旧字形/四库** | 爲→为 巻→卷 眞→真 徳→德 峯→峰 黒→黑 歳→岁 邉→边 衆→众 … | 见全文库 |
| **用户点名** | **髙→高 宻→密 畱→留 戸→户 熈→熙**（另 煕→熙） | residual 必须 0 |
| **多字** | 撒𪻞→撒改 | 金初人名 |

```bash
python3 scripts/normalize_variants.py            # 全活跃库
python3 scripts/normalize_variants.py --dry-run  # 只统计
```

铁律：先 variants 再 resegment/repair；repair 词表跟**简体**；**禁止**只洗单书。

### 原始语料备份

本仓包含 [`data/_raw_no_punct/`](data/_raw_no_punct/) 下的原始文本（繁体/无标点未加工版），保持中间处理后回。  
备份目录（`clean_backup_*`、`user_upload_backup/`）不纳入 Git，仅在本地留存。

---

## 🔗 源与工具

### 文本来源

| 来源 | 链接 | 用途 |
|------|------|------|
| **中文维基文库** | [zh.wikisource.org](https://zh.wikisource.org/) | 多卷有标点公版，MediaWiki API 分页拉取（带速率限制） |
| **殆知阁古籍数据库** | [garychowcmu/daizhigev20](https://github.com/garychowcmu/daizhigev20)（GitHub） | 大规模 UTF-8 史部/子部/集部覆盖；常无标点 → 进隔离区须经自动标点 |
| **Project Gutenberg** | [gutenberg.org](https://www.gutenberg.org/) | 少数短篇公版中文经典 |

公开仓库**只收录公版 / 明确开放许可文本**。非公版现代整理本、受版权保护的译注本等不入库、不进 Git、不在文档中著录来源细节。

### 运行工具

| 工具 | 用途 | 链接 |
|------|------|------|
| **Python 3 `http.server`** | 后端，零依赖 | [docs.python.org](https://docs.python.org/3/library/http.server.html) |
| **OpenCC** | 繁→简转换（`t2s`） | [github.com/BYVoid/OpenCC](https://github.com/BYVoid/OpenCC) |
| **Guwen-biaodian 模型** | 文言文自动标点（PyTorch，CPU） | [github.com/laiche/biaodian](https://github.com/laiche/biaodian) |
| **ripgrep (rg)** | 可选排障（检索默认纯 Python） | [github.com/BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) |
| **gh / git** | 私有仓库托管 | [cli.github.com](https://cli.github.com/) |
| **Node.js** | 前端 JS 语法检查 | [nodejs.org](https://nodejs.org/) |

### 项目脚本

| 脚本 | 作用 |
|------|------|
| [`scripts/auto_punctuate.py`](scripts/auto_punctuate.py) | 模型自动标点（CPU） |
| [`scripts/wait_and_ingest_punct.py`](scripts/wait_and_ingest_punct.py) | 标点完成 → t2s → 入库 |
| [`scripts/fetch_punctuated.py`](scripts/fetch_punctuated.py) | Wikisource 有标点本拉取 |
| [`scripts/fetch_missing_classics.py`](scripts/fetch_missing_classics.py) | 缺书批量补齐（殆知阁等） |
| [`scripts/fetch_liaosong_batch.py`](scripts/fetch_liaosong_batch.py) | 辽宋夏金正史/国志批次 |
| [`scripts/fetch_shiji_full.py`](scripts/fetch_shiji_full.py) | 史记完整拉取 |
| [`scripts/queue_dajin_guozhi_punct.py`](scripts/queue_dajin_guozhi_punct.py) | 大金国志单书标点队列 |
| [`scripts/queue_liaosong_punct.py`](scripts/queue_liaosong_punct.py) | 辽宋批量标点队列 |
| [`scripts/normalize_variants.py`](scripts/normalize_variants.py) | 全活跃库异体/旧字形清洗 |
| [`scripts/resegment_annots.py`](scripts/resegment_annots.py) | 语义分段（chrono/kaoju；四库卷；九帝年谱） |
| [`scripts/repair_false_punct.py`](scripts/repair_false_punct.py) | 专名/年月误断回粘（词表+raw） |
| [`scripts/ingest_dajin_full_after_punct.py`](scripts/ingest_dajin_full_after_punct.py) | 大金全本标点后入库管线 |
| [`docs/segment-and-punct.md`](docs/segment-and-punct.md) | **分段与断句定稿文档** |
| [`docs/variant-map.md`](docs/variant-map.md) | **异体字/旧字形完整映射库** |

---

## 🔌 API 参考

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/health` | — | 存活检测 |
| GET | `/api/periods` | — | 时期 + 书目 + 标签元数据 |
| GET | `/api/search` | `q`, `mode`, `periods`, `books`, `context`, `limit`, `offset` | 全文/书名检索 |
| GET | `/api/text` | `period`, `file` | 全书行数组（阅读器） |

响应字段（search）：`total`（真实总数）、`returned`、`offset`、`has_more`、`terms`、`keywords`。

---

## 🗂 目录结构

```
text-search/
├── server.py               # 后端（Python stdlib）
├── static/index.html       # 前端 SPA
├── .gitignore
├── README.md
├── data/
│   ├── books_meta.json     # 书目 era / author（~117 条）
│   ├── 先秦/ 秦汉/ 魏晋南北朝/ 隋唐五代/
│   ├── 辽宋夏金/ 蒙元/ 明/ 清/   # 活跃语料（简体+有标点，仅公版）
│   │   └── *.txt
│   ├── _raw_no_punct/      # 公版原始文本备份（繁体/无标点）
│   │   └── *.txt
│   │   ├── clean_backup_*/ # (本地) 快照，gitignored
│   │   └── user_upload_*/  # (本地) 不进仓，gitignored
│   └── _cache/             # (本地) 开放源缓存，gitignored
├── scripts/                # 入库/标点/拉取脚本
├── docs/                   # 分段断句 / 异体字库
└── logs/                   # (本地) 日志，gitignored
```

---

## ⚠️ 踩坑记录（运维必读）

| 坑 | 现象 | 修复 |
|----|------|------|
| **假 total → 金史消失** | 搜「兀术」仅有会编/要录，金史不见了 | `search_files` 扫完全书再排序→切片；`total` 必须真实总数 |
| **单线程 HTTPServer 假死** | 手机显示「网络错误」 | 换 `ThreadingHTTPServer` |
| **200 硬截断** | 明知名录有金史但第一页没有 | 默认每页 1000 + `has_more` + 加载更多 |
| **double 简繁文件名** | UI 列出两部「孔子家语」 | 仅保留一条简化文件名；删除繁体同名 |
| **period 筛选置于底栏** | 手机空窗期「请至少选择一个时期」 | 期数选择改粘性顶部折叠 chips |
| **大文件 t2s 超时** | 超大文本全量转换超 agent turn | 先提取纯文本；只对残留繁体做映射 |
| **auto-punct 中途改路径** | 标点完成后写入错误位置 | 标点进行中不挪动目标 `data/` 路径 |
| **Git push 无 TTY** | `git push` 需用户名/密码交互 | `gh auth setup-git` 用 credential helper |
| **auto-punct 专名切开** | `东。平` / `元帅，府` / `天会四，年` | `repair_false_punct` + 词表；**禁**全局按 raw 删句号 |
| **九帝年谱被 peel 碎** | 卷首按「五月」「十二月」拆成多段 | `merge_dajin_nianpu_emperor_blocks`；年谱区跳过时间 peel |
| **正文时间粘连** | `…事。十一月，议割…` 整段过长 | chrono 末道 `peel_inline_time_breaks`（保护【干支】+年事） |
| **残本大金当全本** | ~135KB / plain 约 4 万 | 门控 plain≥约 14–15 万、卷首～四十一 |
| **只修单书异体** | 他书仍见 宻/髙/熈 | `normalize_variants.py` 全活跃库 |

---

## 📜 变更摘要

### 2026-07-18 时期筛选重命名 + 蒙元入库 + 公版门控

- **时期筛选**：`辽宋金夏`→`辽宋夏金`，`元`→`蒙元`，**去掉民国**；数据目录同步改名
- **蒙元活跃 8 部（公版）**：元史、新元史、元朝秘史、圣武亲征录、蒙鞑备录、黑鞑事略、蒙古源流、长春真人西游记
- **书名标签规则**：时代按**原书撰写朝代**
- 公开仓移除非公版文本；README 统计刷新为活跃 92 部
- 改 meta / 时期列表后须 **重启 server.py**，前端 **硬刷新**

### 2026-07-17（夜）异体字库文档化

- 新增 [`docs/variant-map.md`](docs/variant-map.md)：79 单字分类表 + 用户点名键 + 追加 SOP
- `normalize_variants.py` residual 检查含 髙/宻/畱/戸/**熈/煕**
- README 异体表示例改为指向完整库

### 2026-07-17（晚）分段 / 断句定稿沉淀

- 新增 [`docs/segment-and-punct.md`](docs/segment-and-punct.md)：chrono/kaoju、四库卷三层、【干支】岁标、九帝年谱、专名回粘铁律
- 脚本：`normalize_variants.py`、`resegment_annots.py`（年谱整帝合并、时间 peel 跳过年谱区）、`repair_false_punct.py`（含 `海陵炀王` 硬修）
- 大金国志：卷层/干支/年谱结构规则落地；**句内断句仍待继续词表，用户要求暂停正文大改**
- 异体增补：如 熈→熙；全库 variants 可一键洗

### 2026-07-17（初版入库）

- 建成可检索 Web：时期/书筛选、OR/AND 时代排序、阅读器、书名模式
- 入库先秦约 70 部 + 辽宋夏金约 14 部正史/编年/会编（公版）
- 修复：limit 硬截断假 total → 真实总数分页
- 书组收起 / 展开全部书
- 会编/要录：异字映射（含 増 等）+ 语义分段
- GitHub 仓库初始化 + 全 README
- 公版原始语料备份入库

---

## 📄 许可与使用声明

- **代码**（`server.py`、`static/`、`scripts/`）：可用于自托管与二次开发。
- **文本语料**：公开仓库仅收录**公版 / 开放许可**文本（维基文库、daizhige 等）。转载前请自行确认各书授权。
- 非公版现代整理本**不进入本公开仓库**。
- 检索结果仅供文献检索与研究参考，不构成校勘定本。

---

## 🧑‍💻 维护提示

- 改 UI 后需 **Ctrl+F5 / Cmd+Shift+R** 硬刷新
- 新增书 → **先确认公版/开放许可** → 放 `data/<时期>/` → 更新 `books_meta.json` → **重启 8899** → 搜索抽查
- `books_meta` 的 era = **原书撰写时代**
- 自动标点本治理 → 见 [docs/segment-and-punct.md](docs/segment-and-punct.md)
- 端口被占：`fuser -k 8899/tcp` → `python3 -u server.py 8899`
- Git 推送卡验证 → 确保 `gh auth setup-git` 已执行
