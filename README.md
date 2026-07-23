# 古籍全文检索系统

[![Python 3](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://docs.python.org/3/library/http.server.html) · 零外部依赖 · 移动端适配

自托管全文检索 Web 应用，面向中国古典/历史文献。后端纯 Python 标准库实现，前端单页 HTML5。

## 架构

```
project/
├── server.py          # 后端：ThreadingHTTPServer（零依赖）
├── static/
│   └── index.html     # 前端：单页应用（移动端优先）
└── data/
    ├── 先秦/           # 按时代分目录存放文本
    ├── 秦汉/
    ├── 魏晋南北朝/
    ├── 隋唐五代/
    ├── 辽宋夏金/
    ├── 蒙元/
    ├── 明/
    └── 清/
```

- **后端**：Python `http.server.ThreadingHTTPServer`，无需 Flask/FastAPI
- **检索**：Python 纯文本行扫描（标准路径）；可选 ripgrep 预过滤加速
- **前端**：单文件 HTML5，响应式设计，移动端适配
- **存储**：按时代分目录，每书独立 txt 文件

## 快速开始

```bash
git clone <仓库地址>
cd text-search
python3 -u server.py 8899
# 浏览器访问 http://127.0.0.1:8899
```

## API 接口

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 健康检查 |
| `GET /api/periods` | 列出时代分类及书目 |
| `GET /api/search?q=关键词&periods=时代` | 全文检索 |
| `GET /api/text?period=时代&file=书名.txt` | 获取全文正文 |

### 检索语法

| 输入 | 含义 | 示例 |
|------|------|------|
| `关键词1+关键词2` | AND（同一行同时出现） | `诸葛亮+北伐` |
| `词A/词B` | OR（任一满足） | `兀术/乌珠` |
| 混合 | OR 组之间 AND | `赵构+秦桧/岳飞` |

空格不是操作符，作为普通字符处理。结果按史料朝代从早到晚排序。

## 功能特性

- **时代筛选**：顶部标签栏快速切换，支持多选
- **书目筛选**：在选定时代内按书勾选
- **结果排序**：按史料年代（早→晚）、同书按行号
- **全文阅读器**：跳转行号、字号调节（A−/A+）、前后文展开
- **书中检索**：在阅读器中搜索关键词，上一处/下一处跳转
- **字体选择**：系统默认 / 霞鹜文楷
- **查询模式**：全文检索 / 书名检索双模式

## 部署说明

推荐使用 nginx 反向代理 + TLS：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8899;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

服务默认绑定 `127.0.0.1` 而非 `0.0.0.0`，避免绕过 nginx 直接访问。

## 版权说明

- 本仓库仅包含**搜索系统代码**，不包含任何古籍文本数据
- 文本数据（`data/` 目录）需由用户自行准备公版来源（如维基文库、殆知阁、Project Gutenberg 等）
- 禁止将未授权现代译注/校注本上传至公开仓库

## 依赖

- Python 3.8+（仅标准库）
- 可选：ripgrep（`rg`，用于加速检索）
- 可选：OpenCC（简繁转换工具）

## 许可

MIT License
