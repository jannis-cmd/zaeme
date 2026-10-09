import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from agents_gateway import AgentsGateway


class AgentsGatewayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.bundle = Path(self.folder.name) / 'bundle.js'
        self.bundle.write_text('/* synthetic SDK */')
        self.patch = patch.object(AgentsGateway, 'bundle', self.bundle)
        self.patch.start()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), lambda *a, **kw: AgentsGateway(*a, directory='.', **kw))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.patch.stop()
        self.folder.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_main_loads_agent_and_preserves_profile_storage(self):
        status, html = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'voice-agent.js?v=1', html)
        status, script = self.request('GET', '/app.js')
        self.assertIn(b'hearth.guest.v3', script)
        self.assertNotIn(b'hearth.agents-test.v3', script)
        self.assertEqual(self.request('GET', '/voice-agent.js'), (200, b'/* synthetic SDK */'))

    def test_legal_pages_are_public_without_voice_sdk(self):
        for route, heading in [('/impressum', 'Impressum'), ('/datenschutz', 'Datenschutzerklärung')]:
            with self.subTest(route=route):
                status, body = self.request('GET', route)
                self.assertEqual(status, 200)
                self.assertIn(heading.encode(), body)
                self.assertIn(b'Myna Technologies Jannis Erni', body)
                self.assertNotIn(b'<script', body)
                self.assertEqual(self.request('HEAD', route), (200, b''))
        self.assertEqual(self.request('GET', '/legal.css')[0], 200)

    def test_no_source_or_secret_served(self):
        for method in ('GET', 'HEAD'):
            for path in ('/agents_service.py', '/agents_gateway.py', '/.env.example', '/dist/', '/package-lock.json'):
                self.assertEqual(self.request(method, path)[0], 404)

    def test_cross_origin_cannot_issue_token(self):
        with patch('agents_gateway.session') as session:
            status, _ = self.request('POST', '/api/agents/session', b'{}', {'Origin': 'https://other.test'})
        self.assertEqual(status, 403)
        session.assert_not_called()

    def test_budget_fallback_is_returned_to_client(self):
        with patch('agents_gateway.session', return_value={'backend': 'classic', 'reason': 'allowance'}):
            status, body = self.request('POST', '/api/agents/session', b'{"profiles":[{"name":"Test"}]}')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['backend'], 'classic')
