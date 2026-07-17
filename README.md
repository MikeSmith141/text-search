# 📚 史料检索（text-search）

[![Python 3](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://docs.python.org/3/library/http.server.html) | [![Private](https://img.shields.io/badge/visibility-private-red)](https://github.com/MikeSmith141/text-search) | 零依赖 | 移动端可用

**零依赖、可自托管的中国古典/史料全文检索 Web 应用。**  
后端纯 Python 标准库（`http.server`），前端单页 HTML 无框架，数据为 `data/<时期>/<书名>.txt` 扁平文件。  
手机 / 桌面均可使用；**史料时代排序**、**书级勾选**、**OR/AND 检索**、**全文阅读器**。

> 仓库为 **Private**，语料来源详见 [源与工具](#-源与工具)。

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
| | 标签展示 | `书名·[时代]·作者`（来自 `books_meta.json`） |
| 📖 **阅读器** | 打开定位 / 阅读全书 | 任意命中→「打开定位」跳转行、书组头「阅读全书」 |
| | 字号 A± / 行跳转 / 进度条 | 大书按约 400 行窗口分段加载 |
| | **在本书中检索** | 同一套 `/` `+` 语法；上一处/下一处按 OR 感知 terms |
| 🛠 **语料治理** | 异体字映射 | 扩展区字形（㑹→会）+ 日文新字体（増→增、従→从等） |
| | 语义分段（编年类） | 保护 `【…】` 注释；按年号年、季节、干支、引书句式断段 |
| | 简体+有标点门控 | 活跃库必须简体有标点；原料放 `_raw_no_punct/` 隔离 |
| | 自动标点队列 | CPU 模型给无标点本加标点后自动入库 |

---

## 📊 语料统计

| 时期目录 | 活跃书数 | 代表性书籍 | 原始字节 |
|----------|----------|-----------|----------|
| **先秦** | ~72 部 | 史记、资治通鉴、春秋左传、论语、孟子、韩非子、庄子、楚辞、尚书、绎史、路史…… | ~52 MB |
| **秦汉** | 0（占位） | — | — |
| **魏晋南北朝** | 0（占位） | — | — |
| **隋唐五代** | 0（占位） | — | — |
| **辽宋金夏** | 13 部 | 宋史、辽史、金史、三朝北盟会编、建炎以来系年要录、续资治通鉴长编（及拾补）、契丹国志、金史纪事本末…… | ~53 MB |
| **元** | 0（占位） | — | — |
| **明** | 0（占位） | — | — |
| **清** | 0（占位） | — | — |
| **民国** | 0（占位） | — | — |
| **隔离区** | `_raw_no_punct/*.txt` | 大金国志、东都事略、宋史纪事本末、七国考、路史、绎史（原料）…… | ~16 MB |
| **总计（活跃）** | **~85 部** | 简体+有标点 | **~105 MB** |

> 完整书单见 [`data/books_meta.json`](data/books_meta.json)。

---

## 📋 史料入库流程

```
用户文件 / 开放源下载
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
│ □ 许可 → 公版/用户自备/    │
│   开放API                  │
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
│ □ 搜索抽查（如「完颜亮」）  │
└─────────────────────────────┘
```

### 异体字映射表（示例）

| Category | Examples | Map to |
|----------|----------|--------|
| **CJK Ext A/B** | 㑹 㸃 㡬 䟽 䧟 㮚 䝉 䕶 㓂 㕘 | 会 点 几 疏 陷 栗 蒙 护 寇 参 |
| **Japanese shinjitai** | 増 乗 従 収 両 恵 隠 | 增 乘 从 收 两 惠 隐 |
| **Common variants** | 説 録 舎 暦 爲 涙 焼 抜 挿 | 说 录 舍 历 为 泪 烧 拔 插 |

### 原始语料备份

本仓包含 [`data/_raw_no_punct/`](data/_raw_no_punct/) 下的原始文本（繁体/无标点未加工版），保持中间处理后回。  
备份目录（`clean_backup_*`、`user_upload_backup/`）不纳入 Git，仅在本地留存。

---

## 🔗 源与工具

### 文本来源

| 来源 | 链接 | 用途 |
|------|------|------|
| **用户自备**（优先） | — | 购买的中华书局 epub、自行整理的 txt（如长编、要录、会编、战国史料编年辑证等） |
| **中文维基文库** | [zh.wikisource.org](https://zh.wikisource.org/) | 多卷有标点本，MediaWiki API 分页拉取（带速率限制） |
| **殆知阁古籍数据库** | [garychowcmu/daizhigev20](https://github.com/garychowcmu/daizhigev20)（GitHub） | 大规模 UTF-8 史部/子部/集部覆盖；常无标点 → 进隔离区须经自动标点 |
| **Project Gutenberg** | [gutenberg.org](https://www.gutenberg.org/) | 少数短篇公版中文经典 |

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
| [`scripts/fetch_liaosong_batch.py`](scripts/fetch_liaosong_batch.py) | 辽宋金夏正史/国志批次 |
| [`scripts/fetch_shiji_full.py`](scripts/fetch_shiji_full.py) | 史记完整拉取 |
| [`scripts/queue_dajin_guozhi_punct.py`](scripts/queue_dajin_guozhi_punct.py) | 大金国志单书标点队列 |
| [`scripts/queue_liaosong_punct.py`](scripts/queue_liaosong_punct.py) | 辽宋批量标点队列 |

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
│   ├── books_meta.json     # 113 条书目的 era / author
│   ├── 先秦/ … 民国/       # 活跃语料（简体+有标点）
│   │   └── *.txt
│   ├── _raw_no_punct/      # 原始文本备份（繁体/无标点）
│   │   └── *.txt           # 16 文件，~16 MB
│   │   ├── clean_backup_*/ # (本地) 去污染前快照，gitignored
│   │   └── user_upload_*/  # (本地) 用户上传原稿，gitignored
│   └── _cache/             # (本地) 开放源缓存，gitignored
├── scripts/                # 入库/标点/拉取脚本
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
| **EPUB 全 t2s 超时** | 长编 20 MB 转换超 agent turn | 先提取纯文本；只对残留繁体做映射 |
| **auto-punct 中途改路径** | 标点完成后写入错误位置 | 标点进行中不挪动目标 `data/` 路径 |
| **Git push 无 TTY** | `git push` 需用户名/密码交互 | `gh auth setup-git` 用 credential helper |

---

## 📜 变更摘要

### 2026-07-17（初版入库）

- 建成可检索 Web：时期/书筛选、OR/AND 时代排序、阅读器、书名模式
- 入库先秦 ~72 部 + 辽宋金夏 ~13 部正史/编年/会编
- 用户 epub/txt 优先清洗（长编、要录、会编）
- 修复：limit 硬截断假 total → 真实总数分页
- 书组收起 / 展开全部书
- 会编/要录：异字映射（含 増 等）+ 语义分段
- 私有 GitHub 仓库初始化 + 全 README
- 原始语料备份上传

---

## 📄 许可与使用声明

- **代码**（`server.py`、`static/`、`scripts/`）：可用于自托管与二次开发。
- **文本语料**：来源混合（公版、维基文库、用户自备整理本）。**本仓库设为 Private**；转载或公开前请自行确认各书版权与整理本授权。
- 检索结果仅供文献检索与研究参考，不构成校勘定本。

---

## 🧑‍💻 维护提示

- 改 UI 后需 **Ctrl+F5 / Cmd+Shift+R** 硬刷新
- 新增书 → 放 `data/<时期>/` → 更新 `books_meta.json` → 搜索抽查
- 端口被占：`fuser -k 8899/tcp` → `python3 -u server.py 8899`
- Git 推送卡验证 → 确保 `gh auth setup-git` 已执行
