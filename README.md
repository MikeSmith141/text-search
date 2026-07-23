# 古籍全文检索系统

[![Python 3](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://docs.python.org/3/library/http.server.html) · 零外部依赖 · 移动端适配 · 自托管

自托管全文检索 Web 应用，面向中国古典/历史文献。后端纯 Python 标准库实现，前端单页 HTML5 应用，移动端优先。

---

## 功能总览

| 功能 | 说明 |
|------|------|
| **全文检索** | 支持 AND/OR 组合查询，结果按史料年代排序 |
| **时代筛选** | 按时代标签快速切换，支持多时代同时检索 |
| **书目筛选** | 在选定时代内按具体书目勾选 |
| **全文阅读器** | 行号跳转、字号调节 (A−/A+)、前后文展开 |
| **书中检索** | 阅读器中搜索关键词，上一处/下一处跳转 |
| **多字体** | 系统默认 / 霞鹜文楷（LXGW WenKai） |
| **双模式** | 全文检索 / 书名检索 两种查询模式 |

### 全文阅读器

书目搜索结果中点击"阅读全书"或结果行中"打开定位"，进入全文阅读模式。支持字体缩放、行号跳转、展开前后文、书中二次检索。

---

## 检索语法

| 语法 | 含义 | 示例 |
|------|------|------|
| `A+B` | **AND** — 同一行同时出现 A 和 B | `诸葛亮+北伐` |
| `A/B` | **OR** — 出现 A 或 B 即可 | `兀术/乌珠/宗弼` |
| `(A/B)+C` | **混合** — (A或B) 且 C | `(岳飞/岳武穆)+十二金牌` |

> 注意：空格不是操作符，作为普通字符处理。检索 `「无恤 毋恤」` 会搜索包含"无恤 毋恤"整串的行。

查询时同义词组可用 `/` 分隔（如 `太后/高后/吕后`），不同条件用 `+` 拼接（如 `吕后+匈奴`）。

---

## 快速开始

```bash
git clone <仓库地址>
cd text-search
python3 -u server.py 8899
# 浏览器打开 http://127.0.0.1:8899
```

### 准备语料

在 `data/` 下按时代分目录存放 `.txt` 文件：

```
data/
├── 先秦/    论语.txt  孟子.txt  左传.txt  ...
├── 秦汉/    史记.txt  汉书.txt    ...
├── 魏晋南北朝/
├── 隋唐五代/
├── 辽宋夏金/  宋史.txt  辽史.txt  ...
├── 蒙元/    元史.txt  ...
├── 明/
└── 清/
```

每本书一个 txt 文件，UTF-8 编码。`books_meta.json` 记录每本书的朝代和作者信息，用于排序和显示标签。

---

## API 文档

### `GET /api/health`

健康检查，返回 `{"status": "ok"}`。

### `GET /api/periods`

列出所有时代分类及各时代的书目信息。

```json
{
  "periods": [
    {
      "name": "先秦",
      "books": [
        {"book": "论语", "era": "春秋", "author": "孔子弟子及再传弟子", "size": 69043}
      ],
      "total_books": 1
    }
  ]
}
```

### `GET /api/search`

全文检索。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 查询关键词，支持 `+`(AND) 和 `/`(OR) |
| `periods` | string | 否 | 限定时代，逗号分隔（如 `先秦,秦汉`） |
| `books` | string | 否 | 限定书目，逗号分隔（如 `先秦/论语,秦汉/史记`） |
| `mode` | string | 否 | 检索模式：`fulltext`（全文，默认）/ `title`（仅书名） |
| `context` | int | 否 | 前后文行数（默认 1） |
| `limit` | int | 否 | 最大返回条数（默认 1000） |
| `offset` | int | 否 | 分页偏移（默认 0） |

**返回示例：**

```json
{
  "query": "诸葛亮+北伐",
  "keywords": ["诸葛亮", "北伐"],
  "total": 42,
  "returned": 42,
  "offset": 0,
  "limit": 1000,
  "has_more": false,
  "results": [
    {
      "period": "秦汉",
      "book": "三国志",
      "era": "西晋",
      "author": "陈寿",
      "label": "三国志·[西晋]·陈寿",
      "line": 1523,
      "text": "……诸葛亮率诸军北伐……",
      "context": [
        {"line": 1522, "text": "……前文……", "is_match": false},
        {"line": 1523, "text": "……诸葛亮率诸军北伐……", "is_match": true},
        {"line": 1524, "text": "……后文……", "is_match": false}
      ]
    }
  ]
}
```

### `GET /api/text`

获取全书正文，用于阅读器。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `period` | string | 是 | 时代目录名 |
| `file` | string | 是 | 文件名（含 `.txt`） |

返回每行文本及行号，默认每页约 400 行，支持前后翻页。

---

## 部署指南

### 生产部署（nginx 反向代理）

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8899;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

服务绑定 `127.0.0.1`，禁止直接暴露 `IP:端口` 访问。

### 速率限制（可选）

```nginx
limit_req_zone $binary_remote_addr zone=history:10m rate=5r/m;

server {
    location / {
        limit_req zone=history burst=3 nodelay;
        proxy_pass http://127.0.0.1:8899;
    }
}
```

### 后台运行

```bash
# 启动
nohup python3 -u server.py 8899 > server.log 2>&1 &

# 查看
tail -f server.log

# 停止
kill $(lsof -ti:8899)
```

或使用 systemd 服务管理。

---

## 技术架构

### 后端（server.py）

- 纯 Python 标准库（`http.server.ThreadingHTTPServer`）
- 零依赖，不需要 pip install
- 多线程处理并发请求
- 纯 Python 行扫描 + 可选 ripgrep 预过滤
- 路径穿越防护

### 前端（static/index.html）

- 单文件 HTML5，无框架
- 响应式设计：手机 / 平板 / 桌面 三档适配
- CSS 变量驱动主题
- localStorage 持久化偏好设置（字体、字号、预览模式）

### 检索引擎

1. 解析查询：`+` → AND 组，`/` → OR 组
2. 遍历选定时代目录的 txt 文件
3. 可选 `rg -l` 预过滤（快速排除无匹配文件）
4. Python 逐行匹配并提取前后文
5. 按史料年代（`era` 字段）从早到晚排序
6. 返回分页结果

---

## 常见问题

**Q: 启动后页面能打开，但搜索返回 0 条结果？**
A: 确认 `data/` 下已有 txt 文件。检查控制台 Network 请求，查看返回的 `debug` 字段确认查询参数是否正确编码。

**Q: 搜索中文时乱码？**
A: 确保 txt 文件为 UTF-8 编码。前端使用 `encodeURIComponent` 编码 URL 参数。

**Q: 服务偶尔卡住 / 无响应？**
A: 使用了 `ThreadingHTTPServer`（非单线程），但长时间 I/O 仍可能阻塞。确保 `data/` 下无超大单文件，或配置 ripgrep 加速。

**Q: ip:port 能直接访问，不安全？**
A: 服务默认绑定 `127.0.0.1`。如果可公网访问，请检查启动参数是否误设为 `0.0.0.0`，并使用 nginx 反向代理。

---

## 许可

MIT License

---

## 致谢

- [殆知阁古籍文献库](https://github.com/garychowcmu/daizhigev20) - 公版古籍来源
- [维基文库](https://zh.wikisource.org/) - 公版古籍来源
- [Project Gutenberg](https://www.gutenberg.org/) - 公版古籍来源
- [OpenCC](https://github.com/BYVoid/OpenCC) - 简繁转换
- [ripgrep](https://github.com/BurntSushi/ripgrep) - 高性能文本搜索
- [霞鹜文楷](https://github.com/lxgw/LxgwWenKai) - 开源中文字体
