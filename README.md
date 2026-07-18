# Classical Text Search

[![Python 3](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://docs.python.org/3/library/http.server.html) · zero runtime deps · mobile-friendly

A self-hosted full-text search app for **public-domain Chinese classical / historical texts**.

- Backend: Python stdlib only (`ThreadingHTTPServer`)
- Frontend: single-page `static/index.html` (no framework)
- Corpus: flat files under `data/<period>/<title>.txt`

Features: period filters, per-book selection, `/` OR and `+`/space AND queries, chronological hit ordering, and an in-browser reader.

---

## Quick start

```bash
cd /path/to/text-search
python3 -u server.py 8899
# open http://127.0.0.1:8899
```

### Query syntax

| Input | Meaning | Example |
|------|---------|---------|
| `A B` | AND (both terms) | `兀术 金史` |
| `A/B` | OR (either term) | `兀术/乌珠/宗弼` |
| `A+B` | AND on same line | `无恤+伯鲁` |
| mixed | OR groups AND-ed | `兀术/乌珠+宗弼 金史` |

---

## Features

| Area | Feature | Notes |
|------|---------|-------|
| Search | Full-text | Line scan over active `data/**/*.txt` |
| | Title search | Match book name / label / author / era |
| | Book filter | `books=period/title,...` |
| | Pagination | Real `total` + `has_more` + load more |
| Sort | Source era order | From early to late via `ERA_ORDER` |
| UI | Group by book | Collapse / expand hit groups |
| | Reader | Jump to line, font size, in-book search |
| Corpus tools | Variant normalize | `scripts/normalize_variants.py` |
| | Resegment | `scripts/resegment_annots.py` (`chrono` / `kaoju`) |
| | Punct repair | `scripts/repair_false_punct.py` |
| | Auto-punct queue | CPU model for unpunctuated raw sources |

---

## Corpus stats (public tree)

| Period dir | Active books | Examples | Size |
|------------|--------------|----------|------|
| **先秦** | 70 | 史记, 资治通鉴, 春秋左传, 论语, … | ~41 MB |
| **秦汉** | 0 | placeholder | — |
| **魏晋南北朝** | 0 | placeholder | — |
| **隋唐五代** | 0 | placeholder | — |
| **辽宋夏金** | 14 | 宋史, 辽史, 金史, 三朝北盟会编, … | ~53 MB |
| **蒙元** | 8 | 元史, 新元史, 元朝秘史, 圣武亲征录, … | ~12 MB |
| **明** | 0 | placeholder | — |
| **清** | 0 | placeholder | — |
| **Isolation** | `_raw_no_punct/*.txt` | unpunctuated / traditional raw sources | ~34 MB |
| **Total active** | **92** | Simplified Chinese + punctuation | **~105 MB** |

Metadata: [`data/books_meta.json`](data/books_meta.json) (~117 entries).

**Public repository policy:** only **public-domain / clearly open-licensed** texts are shipped. Modern copyrighted editions are not stored in this repo and are not documented here.

---

## Ingest flow

```
public / open sources
       │
       ▼
┌─────────────────────────────┐
│ 1. Pre-ingest checks        │
│ □ Simplified (OpenCC t2s)   │
│ □ Punctuation density gate  │
│ □ UTF-8 encoding            │
│ □ Variant map cleanup       │
│ □ Volume integrity          │
│ □ License = PD / open only  │
└─────────────────────────────┘
       │ pass? → 3
       ▼
┌─────────────────────────────┐
│ 2. Isolation (_raw_no_punct)│
│    keep unpunctuated/trad.  │
│    optional auto-punct queue │
└─────────────────────────────┘
       ▼
┌─────────────────────────────┐
│ 3. Active ingest            │
│    data/<period>/<title>.txt│
│    update books_meta.json   │
└─────────────────────────────┘
       ▼
┌─────────────────────────────┐
│ 4. Verify + restart server  │
└─────────────────────────────┘
```

Raw PD sources live under [`data/_raw_no_punct/`](data/_raw_no_punct/). Local scratch dirs (`clean_backup_*`, `user_upload_*`, `_cache/`) are gitignored.

---

## Sources & tools

### Text sources (public-domain / open)

| Source | Link | Role |
|--------|------|------|
| **Chinese Wikisource** | [zh.wikisource.org](https://zh.wikisource.org/) | Punctuated public-domain multi-volume texts |
| **daizhigev20** | [garychowcmu/daizhigev20](https://github.com/garychowcmu/daizhigev20) | Large UTF-8 classical dump (often unpunctuated) |
| **Project Gutenberg** | [gutenberg.org](https://www.gutenberg.org/) | A few short Chinese public-domain works |

### Runtime tools

| Tool | Role | Link |
|------|------|------|
| Python 3 `http.server` | backend | [docs.python.org](https://docs.python.org/3/library/http.server.html) |
| OpenCC | traditional → simplified | [github.com/BYVoid/OpenCC](https://github.com/BYVoid/OpenCC) |
| Guwen-biaodian model | auto punctuation (CPU) | [github.com/laiche/biaodian](https://github.com/laiche/biaodian) |
| ripgrep (optional) | debugging | [github.com/BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) |
| gh / git | hosting | [cli.github.com](https://cli.github.com/) |

### Scripts

| Script | Role |
|--------|------|
| [`scripts/auto_punctuate.py`](scripts/auto_punctuate.py) | CPU auto-punctuation |
| [`scripts/wait_and_ingest_punct.py`](scripts/wait_and_ingest_punct.py) | wait → t2s → ingest |
| [`scripts/fetch_punctuated.py`](scripts/fetch_punctuated.py) | Wikisource fetch |
| [`scripts/fetch_missing_classics.py`](scripts/fetch_missing_classics.py) | batch fill from daizhige etc. |
| [`scripts/normalize_variants.py`](scripts/normalize_variants.py) | variant / kyujitai cleanup |
| [`scripts/resegment_annots.py`](scripts/resegment_annots.py) | semantic resegmentation |
| [`scripts/repair_false_punct.py`](scripts/repair_false_punct.py) | false punctuation repair |
| [`docs/segment-and-punct.md`](docs/segment-and-punct.md) | segmentation rules |
| [`docs/variant-map.md`](docs/variant-map.md) | variant map |

---

## API

| Method | Path | Params | Notes |
|--------|------|--------|-------|
| GET | `/api/health` | — | liveness |
| GET | `/api/periods` | — | periods + books + labels |
| GET | `/api/search` | `q`, `mode`, `periods`, `books`, `context`, `limit`, `offset` | full-text / title |
| GET | `/api/text` | `period`, `file` | full line array for reader |

Search response includes `total`, `returned`, `offset`, `has_more`, `terms`, `keywords`.

---

## Layout

```
text-search/
├── server.py
├── static/index.html
├── .gitignore
├── README.md
├── data/
│   ├── books_meta.json
│   ├── 先秦/ 秦汉/ 魏晋南北朝/ 隋唐五代/
│   ├── 辽宋夏金/ 蒙元/ 明/ 清/
│   ├── _raw_no_punct/          # public-domain raw sources
│   └── _cache/                 # local only (gitignored)
├── scripts/
├── docs/
└── logs/                       # local only (gitignored)
```

Optional local-only overlay (not committed): `data/books_meta.local.json` is merged at runtime if present.

---

## Ops notes

| Issue | Fix |
|-------|-----|
| Fake `total` hiding later books | Scan all hits, then sort/slice; return real total |
| Single-thread hang | Use `ThreadingHTTPServer` |
| Hard page cap | Default page size 1000 + load more |
| Duplicate simplified/traditional filenames | Keep one simplified stem |
| Auto-punct path moved mid-job | Do not move target path while job runs |
| Proper-name false splits | `repair_false_punct` + lexicon; never global-delete periods |

---

## Changelog (high level)

### 2026-07-18
- Period chips: `辽宋金夏` → `辽宋夏金`, `元` → `蒙元`; drop 民国 chip
- Public-domain-only corpus for the public tree (92 active books)
- English product UI / README
- Optional local meta overlay for private runtime use

### 2026-07-17
- Initial searchable web app
- Variant map + segmentation docs/scripts
- Pre-Qin + Liao-Song-Xia-Jin public-domain ingest

---

## License & notice

- **Code** (`server.py`, `static/`, `scripts/`): free to self-host and modify.
- **Texts in this public repo**: public-domain / open-licensed sources only. Verify licensing before redistribution.
- Search output is for research convenience, not a critical edition.

---

## Maintainer tips

- After UI changes: hard refresh (`Ctrl+F5` / `Cmd+Shift+R`)
- Add a book: confirm public-domain / open license → put under `data/<period>/` → update `books_meta.json` → restart port 8899 → spot-check search
- `books_meta.era` = original composition era
- Segmentation rules: [docs/segment-and-punct.md](docs/segment-and-punct.md)
- Free port: `fuser -k 8899/tcp` then `python3 -u server.py 8899`
