import json
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from web_service import create_app
from guest_access import GUEST_SECONDS
import websocket
from werkzeug.serving import make_server, WSGIRequestHandler
from simple_websocket import Server as WebSocketServer


class GuestAccessTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = dict(public_url='https://example.com/zaeme', client_id='test',
                           client_secret='test', cookie_secret='test-secret',
                           database=str(Path(self.folder.name) / 'auth.sqlite3'))
        self.access = create_app(self.config).extensions['zaeme_guests']
        self.cookie = self.access.identify(None)
        self.payload = dict(signed_url='wss://api.elevenlabs.io/v1/convai/conversation?secret=test',
                            reservation='test', profiles='[]', group_rules='', greeting='Hallo', voice_id='test')

    def ticket(self):
        ticket = self.access.reserve(self.cookie)
        self.access.prepare(ticket, self.payload)
        return ticket

    def test_partial_calls_resume_and_exhaust_once_across_restarts(self):
        with patch('guest_access.time.time', return_value=1000):
            ticket = self.ticket()
            self.assertEqual(self.access.open(ticket, self.cookie)[1], 300)
        with patch('guest_access.time.time', return_value=1120):
            self.access.finish(ticket)
            self.access.finish(ticket)  # Idempotent, not double-charged.
            self.assertEqual(self.access.remaining(self.cookie), 180)
            restarted = create_app(self.config).extensions['zaeme_guests']
            self.assertEqual(restarted.remaining(self.cookie), 180)
            ticket = restarted.reserve(self.cookie)
            restarted.prepare(ticket, self.payload)
            self.assertEqual(restarted.open(ticket, self.cookie)[1], 180)
        with patch('guest_access.time.time', return_value=1400):
            restarted.finish(ticket)
            self.assertEqual(restarted.remaining(self.cookie), 0)
            with self.assertRaises(ValueError):
                restarted.reserve(self.cookie)
        # Tomorrow/month later never resets the one-time allowance.
        with patch('guest_access.time.time', return_value=90000):
            with self.assertRaises(ValueError):
                restarted.reserve(self.cookie)

    def test_ticket_is_one_use_and_bound_to_browser(self):
        ticket = self.ticket()
        other = self.access.identify(None)
        with self.assertRaises(ValueError):
            self.access.open(ticket, other)
        self.access.open(ticket, self.cookie)
        with self.assertRaises(ValueError):
            self.access.open(ticket, self.cookie)
        with self.assertRaises(ValueError):
            self.access.reserve(self.cookie)

    def test_abandoned_setup_does_not_consume_time_and_ticket_expires(self):
        with patch('guest_access.time.time', return_value=1000):
            ticket = self.ticket()
        with patch('guest_access.time.time', return_value=1061):
            with self.assertRaises(ValueError):
                self.access.open(ticket, self.cookie)
            self.assertEqual(self.access.remaining(self.cookie), GUEST_SECONDS)
            self.ticket()

    def test_crashed_connection_charged_conservatively_through_deadline(self):
        with patch('guest_access.time.time', return_value=1000):
            ticket = self.ticket()
            self.access.open(ticket, self.cookie)
        restarted = create_app(self.config).extensions['zaeme_guests']
        with patch('guest_access.time.time', return_value=1500):
            self.assertEqual(restarted.remaining(self.cookie), 0)
            with self.assertRaises(ValueError):
                restarted.reserve(self.cookie)

    def test_provider_url_is_encrypted_at_rest_and_cannot_choose_upstream(self):
        self.ticket()
        self.assertNotIn(b'secret=test', Path(self.config['database']).read_bytes())
        for url in ['ws://api.elevenlabs.io', 'wss://evil.example/',
                    'wss://api.elevenlabs.io:8443/v1/convai/conversation',  # gitleaks:allow — forbidden-port URL fixture, not a key
                    'wss://api.elevenlabs.io/private',
                    'wss://user@api.elevenlabs.io/v1/convai/conversation']:
            with self.assertRaises(ValueError):
                self.access.prepare('test', {**self.payload, 'signed_url': url})

    def test_abandoned_encrypted_profile_payloads_are_removed(self):
        with patch('guest_access.time.time', return_value=1000):
            ticket = self.ticket()
        with patch('guest_access.time.time', return_value=1061):
            self.access.identify(self.cookie)
        with self.access.db() as connection:
            self.assertIsNone(connection.execute('SELECT payload FROM guest_calls WHERE ticket=?',
                                                (self.access.hash(ticket),)).fetchone())

    def test_real_websocket_binds_profile_and_closes_at_server_deadline(self):
        class Quiet(WSGIRequestHandler):
            def log(self, *args, **kwargs):
                pass

        class Provider:
            def __init__(self):
                self.messages = queue.Queue()
                self.closed = False
                self.sent = []

            def settimeout(self, timeout):
                pass

            def send(self, message):
                event = json.loads(message)
                self.sent.append(event)
                if event.get('type') == 'conversation_initiation_client_data':
                    self.messages.put(json.dumps({'type': 'conversation_initiation_metadata',
                        'conversation_initiation_metadata_event': {'conversation_id': 'conv_synthetic',
                                                                   'agent_output_audio_format': 'pcm_16000'}}))

            def recv(self):
                try:
                    return self.messages.get(timeout=0.02)
                except queue.Empty:
                    raise websocket.WebSocketTimeoutException()

            def close(self, **kwargs):
                self.closed = True

            def shutdown(self):
                self.closed = True

        original_connect = websocket.create_connection
        accepted_sockets = []

        def accept_socket(*args, **kwargs):
            ws = WebSocketServer(*args, **kwargs)
            accepted_sockets.append(ws.sock)
            return ws

        with patch('guest_access.GUEST_SECONDS', 0.3):
            app = create_app(self.config)
            ticket = self.ticket()
            server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=Quiet)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            provider = Provider()
            try:
                with patch('guest_access.websocket.create_connection', return_value=provider), \
                        patch('web_service.requests.post'), patch('flask_sock.Server', side_effect=accept_socket):
                    cross_site = original_connect(f'ws://127.0.0.1:{server.server_port}/zaeme/voice/{ticket}',
                        host='example.com', origin='https://evil.example',
                        cookie='zaeme_guest=' + self.cookie, subprotocols=['convai'], timeout=3)
                    try:
                        self.assertEqual(cross_site.recv(), '')
                        self.assertEqual(provider.sent, [])
                    finally:
                        cross_site.close()
                        cross_site.shutdown()
                    client = original_connect(f'ws://127.0.0.1:{server.server_port}/zaeme/voice/{ticket}',
                        host='example.com', origin='https://example.com',
                        cookie='zaeme_guest=' + self.cookie, subprotocols=['convai'], timeout=3)
                    try:
                        client.send(json.dumps({'type': 'conversation_initiation_client_data',
                            'dynamic_variables': {'profiles': 'forged'},
                            'conversation_config_override': {'agent': {'prompt': {'prompt': 'forged'}}}}))
                        self.assertEqual(json.loads(client.recv())['type'], 'conversation_initiation_metadata')
                        self.assertEqual(provider.sent[0]['dynamic_variables']['profiles'], self.payload['profiles'])
                        self.assertNotIn('agent', provider.sent[0]['conversation_config_override'])
                        self.assertEqual(client.recv(), '')
                    finally:
                        client.close()
                        client.shutdown()
                    time.sleep(0.05)
                    self.assertTrue(provider.closed)
                    self.assertEqual(self.access.remaining(self.cookie), 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
                # Werkzeug's test WS upgrade hands socket ownership to Flask-Sock.
                for accepted in accepted_sockets:
                    accepted.close()
