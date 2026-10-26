"""Loopback-only prototype HTTP server using Python's standard library."""
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from .documentation import ROOT

STATIC = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/memory.js': ('memory.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
SECURITY_HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, service):
        self.service = service
        self.limits = {}
        self.limit_lock = threading.Lock()
        super().__init__(('127.0.0.1', port), Handler)

    def allow_request(self, address):
        now = time.monotonic()
        with self.limit_lock:
            self.limits = {ip: entry for ip, entry in self.limits.items() if entry[0] > now}
            until, count = self.limits.get(address, (now + 60, 0))
            self.limits[address] = (until, count + 1)
            return count < 20


class Handler(BaseHTTPRequestHandler):
    server_version = 'AgentGuardDocs'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        pass  # Never log question text, request bodies or source passages.

    def send(self, status, value, media_type='application/json'):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8') if media_type == 'application/json' else value
        self.send_response(status)
        for name, setting in SECURITY_HEADERS.items():
            self.send_header(name, setting)
        self.send_header('Content-Type', media_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/status':
            return self.send(200, self.server.service.status())
        if path in STATIC:
            name, media_type = STATIC[path]
            return self.send(200, (ROOT / 'public' / name).read_bytes(), media_type)
        self.send(404, {'error': 'Not found.'})

    def do_POST(self):
        if urlsplit(self.path).path != '/api/chat':
            return self.send(404, {'error': 'Not found.'})
        expected = f'http://127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            return self.send(403, {'error': 'Host not allowed.'})
        allowed_origins = (expected, expected.replace('127.0.0.1', 'localhost'))
        if self.headers.get('Origin') and self.headers['Origin'] not in allowed_origins:
            return self.send(403, {'error': 'Origin not allowed.'})
        if self.headers.get_content_type() != 'application/json':
            return self.send(415, {'error': 'Use application/json.'})
        if self.headers.get('Transfer-Encoding'):
            return self.send(400, {'error': 'Chunked request bodies are not supported.'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            return self.send(400, {'error': 'Invalid content length.'})
        if size < 0:
            return self.send(411, {'error': 'Content length is required.'})
        if size > 100000:
            return self.send(413, {'error': 'Request is too large.'})
        if not self.server.allow_request(self.client_address[0]):
            return self.send(429, {'error': 'Too many requests. Wait a minute and retry.'})
        try:
            body = self.rfile.read(size)
            if len(body) != size:
                return self.send(400, {'error': 'Incomplete request body.'})
            value = json.loads(body)
            result = self.server.service.answer(value)
        except (ValueError, UnicodeError) as error:
            message = 'Invalid JSON.' if isinstance(error, (json.JSONDecodeError, UnicodeError)) else str(error)
            return self.send(400, {'error': message})
        except (TimeoutError, socket.timeout):
            return self.send(408, {'error': 'Request timed out.'})
        except Exception:
            return self.send(500, {'error': 'Search could not be completed. Please retry.'})
        self.send(200, result)

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send(405, {'error': 'Method not allowed.'})

    do_PUT = do_OPTIONS
    do_DELETE = do_OPTIONS
    do_PATCH = do_OPTIONS
