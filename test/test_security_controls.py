import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from security_controls import RequestLimits


class RequestLimitsTest(unittest.TestCase):
    def test_only_configured_proxy_can_supply_client_ip(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'limits.sqlite3'

            @contextmanager
            def db():
                connection = sqlite3.connect(database)
                try:
                    with connection:
                        yield connection
                finally:
                    connection.close()

            limits = RequestLimits(db, 'synthetic-key', ['172.18.0.4/32'])
            for peer, forwarded, expected in (
                    ('172.18.0.4', '198.51.100.1, 203.0.113.2', '203.0.113.2'),
                    ('172.18.0.5', '203.0.113.2', '172.18.0.5'),
                    ('172.18.0.4', 'invalid', '172.18.0.4')):
                self.assertEqual(limits.client(SimpleNamespace(remote_addr=peer,
                    headers={'X-Forwarded-For': forwarded})), expected)
            with patch('security_controls.time.time', return_value=600):
                self.assertTrue(limits.allow('203.0.113.2', 'persona', 1))
                self.assertFalse(limits.allow('203.0.113.2', 'persona', 1))
                self.assertTrue(limits.allow('198.51.100.1', 'persona', 1))
            with patch('security_controls.time.time', return_value=660):
                self.assertTrue(limits.allow('203.0.113.2', 'persona', 1))
            self.assertNotIn(b'203.0.113.2', database.read_bytes())
