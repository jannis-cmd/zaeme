"""Small, durable abuse controls; these are request bursts, not user quotas."""
import hashlib
import hmac
import ipaddress
import time


class RequestLimits:
    def __init__(self, db, secret, trusted_proxies=()):
        self.db = db
        self.secret = secret.encode()
        self.proxies = [ipaddress.ip_network(value) for value in trusted_proxies]
        with db() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS request_limits '
                               '(key TEXT, window INTEGER, used INTEGER NOT NULL, PRIMARY KEY(key, window))')

    def client(self, request):
        peer = ipaddress.ip_address(request.remote_addr or '127.0.0.1')
        if any(peer in network for network in self.proxies):
            # Caddy appends the actual client last and ignores untrusted inbound XFF.
            try:
                return str(ipaddress.ip_address(request.headers.get('X-Forwarded-For', '').split(',')[-1].strip()))
            except ValueError:
                pass
        return str(peer)

    def allow(self, client, scope, maximum):
        window = int(time.time()) // 60
        key = hmac.new(self.secret, (scope + ':' + client).encode(), hashlib.sha256).hexdigest()
        with self.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('DELETE FROM request_limits WHERE window<?', (window - 1,))
            connection.execute('INSERT INTO request_limits VALUES (?, ?, 1) '
                               'ON CONFLICT(key,window) DO UPDATE SET used=used+1', (key, window))
            used = connection.execute('SELECT used FROM request_limits WHERE key=? AND window=?',
                                      (key, window)).fetchone()[0]
        return used <= maximum
