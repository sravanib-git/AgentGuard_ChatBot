import http.client
import json
import threading
import unittest
from lib.server import LocalServer
from lib.service import SupportService


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = LocalServer(0, SupportService())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    def post(self, value, headers=None):
        return self.request('POST', '/api/chat', json.dumps(value), {'Content-Type': 'application/json', **(headers or {})})

    def test_ui_status_and_private_files(self):
        for path in ('/', '/style.css', '/app.js', '/memory.js'):
            status, headers, _ = self.request('GET', path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertIn('Content-Security-Policy', headers)
        status, _, body = self.request('GET', '/api/status')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['application'], 'agentguard-documentation-final')
        for path in ('/.env', '/data/knowledge.json', '/lib/service.py', '/../run.py'):
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_request_limits(self):
        self.assertEqual(self.post({'question': 'Install Python SDK'})[0], 200)
        self.assertEqual(self.post({})[0], 400)
        self.assertEqual(self.post({'question': 'hi'}, {'Origin': 'https://evil.test'})[0], 403)
        self.assertEqual(self.request('POST', '/api/chat', '{}')[0], 415)
        # The server rejects oversized lengths before reading the body. Sending
        # an unread body can reset the connection on Windows before we read 413.
        self.assertEqual(self.request('POST', '/api/chat', '', {'Content-Type': 'application/json', 'Content-Length': '100001'})[0], 413)
        self.assertEqual(self.request('PUT', '/api/chat')[0], 405)
        self.assertEqual(self.request('POST', '/api/chat', '{', {'Content-Type': 'application/json'})[0], 400)
        for _ in range(21):
            result = self.post({'question': 'hi'})
        self.assertEqual(result[0], 429)

    def test_empty_and_ambiguous_questions(self):
        for question in ('', ' ', '\t\n'):
            with self.subTest(question=question):
                status, _, body = self.post({'question': question})
                self.assertEqual(status, 400)
                self.assertIn('question', json.loads(body)['error'])
        for question in ('How do I configure...', 'How do I configure it?', 'how'):
            with self.subTest(question=question):
                status, _, body = self.post({'question': question})
                result = json.loads(body)
                self.assertEqual(status, 200)
                self.assertEqual(result['status'], 'clarification')
                self.assertEqual(result['sources'], [])
