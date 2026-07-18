#!/usr/bin/env python3
"""Classical text search v2 - backend service"""
import json
import os
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
META_PATH = os.path.join(DATA_DIR, 'books_meta.json')
META_LOCAL_PATH = os.path.join(DATA_DIR, 'books_meta.local.json')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
}


def load_meta():
    """Load public meta, then optional local-only overlay (not for git)."""
    data = {}
    try:
        with open(META_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update(raw)
    except Exception:
        pass
    try:
        if os.path.exists(META_LOCAL_PATH):
            with open(META_LOCAL_PATH, 'r', encoding='utf-8') as f:
                local = json.load(f)
            if isinstance(local, dict):
                data.update(local)
    except Exception:
        pass
    return data


BOOK_META = load_meta()


def book_info(book_name: str) -> dict:
    """Return book meta and display label: title·[era]·author"""
    meta = BOOK_META.get(book_name) or {}
    # compat: title-chapter style stems
    if not meta and '-' in book_name:
        meta = BOOK_META.get(book_name.split('-', 1)[0]) or {}
    era = (meta.get('era') or '').strip()
    author = (meta.get('author') or '').strip()
    parts = [book_name]
    if era:
        parts.append(f'[{era}]')
    if author:
        parts.append(author)
    label = '·'.join(parts) if len(parts) > 1 else book_name
    return {
        'era': era,
        'author': author,
        'label': label,
    }


def format_size(n: int) -> str:
    f = float(n)
    for u in ('B', 'KB', 'MB', 'GB'):
        if f < 1024:
            return f'{f:.1f}{u}'
        f /= 1024
    return f'{f:.1f}TB'


FIXED_PERIODS = ['先秦', '秦汉', '魏晋南北朝', '隋唐五代', '辽宋夏金', '蒙元', '明', '清']

# source composition era labels, early -> late
ERA_ORDER = [
    '远古', '上古', '夏', '商', '西周', '西周至春秋', '春秋', '战国', '先秦',
    '秦', '西汉', '东汉', '汉',
    '三国', '三国魏', '三国蜀', '三国吴',
    '西晋', '东晋', '南朝宋', '南朝齐', '梁', '南朝梁', '南朝陈',
    '北魏', '东魏', '西魏', '北齐', '北周', '魏晋',
    '隋', '唐', '五代', '后梁', '后唐', '后晋', '后汉', '后周',
    '辽', '北宋', '南宋', '宋', '金', '西夏',
    '蒙元', '元', '明', '清', '民国', '现代',
]


def era_sort_key(era: str) -> tuple:
    """Sort by source era early->late; unknown last."""
    era = (era or '').strip()
    if not era:
        return (1, 9999, '')
    try:
        return (0, ERA_ORDER.index(era), era)
    except ValueError:
        # 模糊匹配：如「西汉初」→ 西汉
        for i, name in enumerate(ERA_ORDER):
            if name and name in era:
                return (0, i, era)
        return (1, 9999, era)


def list_periods():
    """始终返回固定时期列表，即使目录为空也显示。"""
    existing = {}
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            if name.startswith('_'):
                continue
            dirpath = os.path.join(DATA_DIR, name)
            if not os.path.isdir(dirpath):
                continue
            books = []
            for fname in sorted(os.listdir(dirpath)):
                if not (fname.endswith('.txt') or fname.endswith('.md')):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(fpath)
                    with open(fpath, 'rb') as f:
                        lines = sum(1 for _ in f)
                    books.append({
                        'name': fname.rsplit('.', 1)[0],
                        'file': fname,
                        'size': size,
                        'size_str': format_size(size),
                        'lines': lines,
                        **book_info(fname.rsplit('.', 1)[0]),
                    })
                except OSError:
                    continue
            existing[name] = books

    names = list(FIXED_PERIODS)
    for n in sorted(existing.keys()):
        if n not in names and not n.startswith('_'):
            names.append(n)

    periods = []
    for name in names:
        books = existing.get(name, [])
        periods.append({
            'name': name,
            'books': books,
            'total_books': len(books),
            'total_size_str': format_size(sum(b['size'] for b in books)) if books else '0B',
        })
    return periods


def period_sort_key(name: str) -> tuple:
    """时期从早到晚：固定朝代序优先，未知时期排后。"""
    try:
        return (0, FIXED_PERIODS.index(name), name)
    except ValueError:
        return (1, 999, name)


def parse_query(query: str):
    """解析检索式。

    规则（主君指定）：
    - /  = OR  任一即可   例：无恤/毋恤
    - +  = AND 同时包含   例：无恤+伯鲁
    - 组合：无恤/毋恤+伯鲁 → (无恤 或 毋恤) 且 伯鲁
    - 兼容：|｜ 也当 OR；空格也当 AND（与 + 相同）

    返回：
      terms: list[list[str]]  每组是 OR 候选项，组间 AND
      flat_keywords: list[str]  所有候选项扁平列表（高亮用）
    """
    import re
    q = (query or '').strip()
    if not q:
        return [], []

    # 全角符号归一
    q = q.replace('＋', '+').replace('｜', '|')
    # 运算符两侧空格去掉，避免 "无恤 / 毋恤" 拆坏
    q = re.sub(r'\s*([+/|])\s*', r'\1', q)
    # 其余空白统一成 AND 分隔（与 + 同义）
    q = re.sub(r'\s+', '+', q)

    terms = []
    flat = []
    for part in q.split('+'):
        part = part.strip()
        if not part:
            continue
        # 组内 OR：/ 为主，| 兼容
        alts = [a.strip() for a in re.split(r'[/|]', part) if a.strip()]
        if not alts:
            continue
        seen = set()
        uniq = []
        for a in alts:
            if a not in seen:
                seen.add(a)
                uniq.append(a)
        terms.append(uniq)
        for a in uniq:
            if a not in flat:
                flat.append(a)
    return terms, flat


def line_matches(line: str, terms) -> bool:
    """terms: list[list[str]]，组间 AND，组内 OR。"""
    if not terms:
        return False
    for group in terms:
        if not any(alt in line for alt in group):
            return False
    return True


def search_files(query: str, selected_periods, context_lines: int = 2, limit: int = 200,
                 selected_books=None, offset: int = 0):
    """selected_books: 可选，条目为 '时期/书名' 或 '时期/文件名'；为空则在选中时期内搜全部书。

    关键：
      results  — 分页切片后的命中
      keywords — 扁平关键词（高亮用）
      total    — 全库真实命中总数（未截断）

    重要：必须先扫完全部书、按时代排序，再 offset/limit 截断。
    绝不能用截断后的 len(results) 当作 total——否则南宋大书会把配额吃满，
    金史/宋史等后排书看起来「消失」。
    """
    terms, keywords = parse_query(query)
    if not terms:
        return [], keywords, 0

    # 解析书级过滤：period/book 或 period/file
    book_filter = None  # None=不过滤；set of (period, book_or_file_stem)
    if selected_books:
        book_filter = set()
        for item in selected_books:
            item = (item or '').strip()
            if not item or '/' not in item:
                continue
            period, book_part = item.split('/', 1)
            period = period.strip()
            book_part = book_part.strip()
            if not period or not book_part:
                continue
            stem = book_part.rsplit('.', 1)[0] if book_part.endswith(('.txt', '.md')) else book_part
            book_filter.add((period, stem))
            book_filter.add((period, book_part))

    # target books: fine-sort by source era after scan
    if selected_periods:
        ordered_names = sorted(selected_periods, key=period_sort_key)
        dirs = []
        for p in ordered_names:
            d = os.path.join(DATA_DIR, p)
            if os.path.isdir(d):
                dirs.append((p, d))
    else:
        names = [
            n for n in os.listdir(DATA_DIR)
            if os.path.isdir(os.path.join(DATA_DIR, n)) and not n.startswith('_')
        ]
        dirs = [
            (n, os.path.join(DATA_DIR, n))
            for n in sorted(names, key=period_sort_key)
        ]

    results = []
    for period_name, dirpath in dirs:
        try:
            files = sorted(os.listdir(dirpath))
        except OSError:
            continue
        # sort books by source era so earlier texts are scanned first
        book_files = []
        for fname in files:
            if not (fname.endswith('.txt') or fname.endswith('.md')):
                continue
            book_name = fname.rsplit('.', 1)[0]
            # 书级过滤
            if book_filter is not None:
                if (period_name, book_name) not in book_filter and (period_name, fname) not in book_filter:
                    continue
            info = book_info(book_name)
            book_files.append((era_sort_key(info['era']), book_name, fname, info))
        book_files.sort(key=lambda x: (x[0], x[1]))

        for _era_key, book_name, fname, info in book_files:
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.read().splitlines()
            except OSError:
                continue

            for i, line in enumerate(lines):
                if not line_matches(line, terms):
                    continue
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = [{
                    'line': j + 1,
                    'text': lines[j],
                    'is_match': j == i,
                } for j in range(start, end)]
                results.append({
                    'period': period_name,
                    'book': book_name,
                    'file': fname,
                    'era': info['era'],
                    'author': info['author'],
                    'label': info['label'],
                    'line': i + 1,
                    'text': line,
                    'context': context,
                    'ctx_start': start + 1,
                    'ctx_end': end,
                })

    # books: source era (early->late) -> period dir -> title
    # 同一本书内：目录顺序（行号从前往后）
    results.sort(key=lambda r: (
        era_sort_key(r.get('era') or ''),
        period_sort_key(r.get('period') or ''),
        r.get('book') or '',
        int(r.get('line') or 0),
    ))
    total = len(results)
    offset = max(0, int(offset or 0))
    limit = max(1, int(limit or 200))
    return results[offset:offset + limit], keywords, total


def search_books_by_title(query: str, selected_periods=None, selected_books=None, limit: int = 200, offset: int = 0):
    """书名检索：匹配书名 / 标签 / 作者 / 时代（不搜正文）。

    仍用 parse_query：/ = OR，+ = AND（对书名元数据字段匹配）。
    返回 (results_page, keywords, total)。
    """
    terms, keywords = parse_query(query)
    if not terms:
        return [], keywords, 0

    book_filter = None
    if selected_books:
        book_filter = set()
        for item in selected_books:
            item = (item or '').strip()
            if not item or '/' not in item:
                continue
            period, book_part = item.split('/', 1)
            period = period.strip()
            book_part = book_part.strip()
            if not period or not book_part:
                continue
            stem = book_part.rsplit('.', 1)[0] if book_part.endswith(('.txt', '.md')) else book_part
            book_filter.add((period, stem))
            book_filter.add((period, book_part))

    if selected_periods:
        ordered_names = sorted(selected_periods, key=period_sort_key)
        dirs = []
        for p in ordered_names:
            d = os.path.join(DATA_DIR, p)
            if os.path.isdir(d):
                dirs.append((p, d))
    else:
        names = [
            n for n in os.listdir(DATA_DIR)
            if os.path.isdir(os.path.join(DATA_DIR, n)) and not n.startswith('_')
        ]
        dirs = [
            (n, os.path.join(DATA_DIR, n))
            for n in sorted(names, key=period_sort_key)
        ]

    results = []
    for period_name, dirpath in dirs:
        try:
            files = sorted(os.listdir(dirpath))
        except OSError:
            continue
        for fname in files:
            if not (fname.endswith('.txt') or fname.endswith('.md')):
                continue
            book_name = fname.rsplit('.', 1)[0]
            if book_filter is not None:
                if (period_name, book_name) not in book_filter and (period_name, fname) not in book_filter:
                    continue
            info = book_info(book_name)
            # 拼一段可搜的元数据文本：书名、标签、时代、作者、文件名
            hay = ' '.join([
                book_name,
                info.get('label') or '',
                info.get('era') or '',
                info.get('author') or '',
                fname,
            ])
            if not line_matches(hay, terms):
                continue
            fpath = os.path.join(dirpath, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                size = 0
            results.append({
                'period': period_name,
                'book': book_name,
                'file': fname,
                'era': info['era'],
                'author': info['author'],
                'label': info['label'],
                'size': size,
                'size_str': format_size(size),
            })

    results.sort(key=lambda r: (
        era_sort_key(r.get('era') or ''),
        period_sort_key(r.get('period') or ''),
        r.get('book') or '',
    ))
    total = len(results)
    offset = max(0, int(offset or 0))
    limit = max(1, int(limit or 200))
    return results[offset:offset + limit], keywords, total


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write(f'[{self.address_string()}] {args[0] if args else fmt}\n')
        sys.stderr.flush()

    def _send(self, code: int, body: bytes, content_type: str):
        try:
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self._send(code, body, 'application/json; charset=utf-8')

    def serve_static(self, rel):
        # 防路径穿越
        rel = rel.lstrip('/')
        fp = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not fp.startswith(STATIC_DIR) or not os.path.isfile(fp):
            self.send_json({'error': 'Not Found'}, 404)
            return
        ext = os.path.splitext(fp)[1].lower()
        mime = MIME.get(ext, 'application/octet-stream')
        with open(fp, 'rb') as f:
            content = f.read()
        self._send(200, content, mime)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            params = parse_qs(parsed.query)

            if path == '/api/health':
                self.send_json({'ok': True, 'data_dir': DATA_DIR})
                return

            if path == '/api/periods':
                self.send_json(list_periods())
                return

            if path == '/api/search':
                q = (params.get('q') or [''])[0].strip()
                if not q:
                    self.send_json({'error': '请输入关键词', 'results': [], 'total': 0})
                    return
                selected_raw = (params.get('periods') or [''])[0]
                selected = [s.strip() for s in selected_raw.split(',') if s.strip()] if selected_raw else []
                books_raw = (params.get('books') or [''])[0]
                selected_books = [s.strip() for s in books_raw.split(',') if s.strip()] if books_raw else []
                mode = ((params.get('mode') or ['fulltext'])[0] or 'fulltext').strip().lower()
                if mode in ('title', 'book', 'books', 'name', '书名'):
                    mode = 'title'
                else:
                    mode = 'fulltext'
                try:
                    context = max(0, min(20, int((params.get('context') or ['2'])[0])))
                except ValueError:
                    context = 2
                try:
                    # 默认每页 200；上限放宽到 5000，避免大库命中被硬砍到 200 后「金史消失」
                    limit = max(1, min(5000, int((params.get('limit') or ['200'])[0])))
                except ValueError:
                    limit = 200
                try:
                    offset = max(0, int((params.get('offset') or ['0'])[0]))
                except ValueError:
                    offset = 0

                terms, keywords = parse_query(q)
                if mode == 'title':
                    results, keywords, total = search_books_by_title(
                        q, selected, selected_books, limit, offset
                    )
                    self.send_json({
                        'query': q,
                        'mode': 'title',
                        'keywords': keywords,
                        'terms': terms,
                        'total': total,
                        'returned': len(results),
                        'offset': offset,
                        'limit': limit,
                        'has_more': offset + len(results) < total,
                        'results': results,
                        'periods': selected,
                        'books': selected_books,
                    })
                else:
                    results, keywords, total = search_files(
                        q, selected, context, limit, selected_books, offset
                    )
                    self.send_json({
                        'query': q,
                        'mode': 'fulltext',
                        'keywords': keywords,
                        'terms': terms,
                        'total': total,
                        'returned': len(results),
                        'offset': offset,
                        'limit': limit,
                        'has_more': offset + len(results) < total,
                        'results': results,
                        'periods': selected,
                        'books': selected_books,
                    })
                return

            if path == '/api/text':
                period = (params.get('period') or [''])[0].strip()
                fname = (params.get('file') or [''])[0].strip()
                if not period or not fname:
                    self.send_json({'error': '缺少 period 或 file 参数'}, 400)
                    return
                # 防路径穿越
                if '/' in period or '\\' in period or '..' in period:
                    self.send_json({'error': '非法 period'}, 400)
                    return
                if '/' in fname or '\\' in fname or '..' in fname:
                    self.send_json({'error': '非法 file'}, 400)
                    return
                if not (fname.endswith('.txt') or fname.endswith('.md')):
                    self.send_json({'error': '仅支持 txt/md'}, 400)
                    return
                fpath = os.path.normpath(os.path.join(DATA_DIR, period, fname))
                data_root = os.path.normpath(DATA_DIR)
                if not fpath.startswith(data_root + os.sep) or not os.path.isfile(fpath):
                    self.send_json({'error': '文件不存在'}, 404)
                    return
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.read().splitlines()
                except OSError as e:
                    self.send_json({'error': str(e)}, 500)
                    return
                self.send_json({
                    'period': period,
                    'file': fname,
                    'book': fname.rsplit('.', 1)[0],
                    **book_info(fname.rsplit('.', 1)[0]),
                    'total_lines': len(lines),
                    'lines': lines,
                })
                return

            if path in ('/', '/index.html'):
                self.serve_static('index.html')
                return

            self.serve_static(path.lstrip('/'))
        except Exception as e:
            sys.stderr.write(f'handler error: {e}\n')
            sys.stderr.flush()
            try:
                self.send_json({'error': str(e)}, 500)
            except Exception:
                pass


def main():
    # ensure dirs exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'📜 Classical Text Search is running')
    print(f'   http://0.0.0.0:{PORT}')
    print(f'   data dir: {DATA_DIR}')
    print(f'   press Ctrl+C to stop', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
        server.server_close()


if __name__ == '__main__':
    main()
