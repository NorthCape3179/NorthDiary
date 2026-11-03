"""Serve only bundled scene assets on a private, process-local loopback URL."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import mimetypes
import secrets
import threading
from urllib.parse import unquote, urlsplit


class _AssetsHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, root, fonts, token, **kwargs):
        self.root, self.fonts, self.token = root, fonts, token
        super().__init__(*args, **kwargs)

    def log_message(self, *_):
        pass

    def do_HEAD(self):
        self._respond(False)

    def do_GET(self):
        self._respond(True)

    def _respond(self, body):
        # No directory listing, writes, user data, or general filesystem access.
        path = unquote(urlsplit(self.path).path)
        prefix = '/' + self.token + '/'
        if not path.startswith(prefix):
            self.send_error(404)
            return
        relative = path[len(prefix):] or 'index.html'
        base = self.root
        if relative.startswith('fonts/'):
            key = relative[6:].removesuffix('.ttf')
            if key not in ('fusion-pixel', 'noto-sans-sc', 'noto-serif-sc', 'lxgw-wenkai'):
                self.send_error(404)
                return
            base, relative = self.fonts, key + '/font.ttf'
        try:
            target = (base / relative).resolve()
            if not target.is_relative_to(base) or target.suffix not in (
                '.html', '.js', '.css', '.json', '.svg', '.png', '.webp', '.ttf', '.woff2',
            ) or not target.is_file():
                self.send_error(404)
                return
            data = target.read_bytes()
        except (OSError, ValueError):
            self.send_error(404)
            return
        self.send_response(200)
        kind = {'.js': 'text/javascript', '.ttf': 'font/ttf'}.get(target.suffix)
        self.send_header('Content-Type', kind or mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, max-age=3600')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        if body:
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass


class SceneAssets:
    def __init__(self, root: Path, fonts: Path):
        root, fonts = root.resolve(), fonts.resolve()
        if not (root / 'index.html').is_file():
            raise FileNotFoundError('缺少秋日湖畔页面，请检查场景资源是否完整。')
        token = secrets.token_urlsafe(24)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(
            _AssetsHandler, root=root, fonts=fonts, token=token))
        self.server.daemon_threads = True
        self.url = f'http://127.0.0.1:{self.server.server_port}/{token}/'
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .1}, daemon=True,
                                       name='NorthDiary scene assets')
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=.3)
