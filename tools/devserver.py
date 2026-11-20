"""로컬 미리보기 서버: docs/를 보여주고, 사이트의 ?export 가 보낸 파일을 bake/에 저장한다.

    python tools/devserver.py [포트]

127.0.0.1에서만 열리고, 저장은 bake/ 폴더 안의 정해진 이름만 받는다.
"""
import http.server, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
BAKE = os.path.join(ROOT, 'bake')
NAME_OK = re.compile(r'^[a-z0-9_]+\.(glb|json)$')
MAX = 200 * 1024 * 1024


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DOCS, **kw)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def do_POST(self):
        m = re.match(r'^/__save/([^/?]+)$', self.path)
        n = int(self.headers.get('Content-Length') or 0)
        if not m or not NAME_OK.match(m.group(1)) or n <= 0 or n > MAX:
            self.send_error(400, 'bad save request'); return
        os.makedirs(BAKE, exist_ok=True)
        data = self.rfile.read(n)
        with open(os.path.join(BAKE, m.group(1)), 'wb') as f:
            f.write(data)
        self.send_response(200); self.send_header('Content-Length', '2'); self.end_headers(); self.wfile.write(b'ok')
        print(f'saved bake/{m.group(1)} ({n:,} bytes)', flush=True)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f'serving docs/ on http://127.0.0.1:{port}', flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
