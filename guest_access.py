"""Lifetime guest allowance. Voice travels through the server so the deadline
cannot be bypassed by changing a browser timer or retaining a provider token.
"""
import base64
import hashlib
import json
import secrets
import time
from threading import Event, Thread
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from simple_websocket import ConnectionClosed
import websocket

GUEST_SECONDS = 300


class GuestAccess:
    def __init__(self, db, secret, *, unlimited=False):
        self.db = db
        self.unlimited = unlimited
        self.seconds = 600 if unlimited else GUEST_SECONDS
        self.cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
        with db() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS guests (id TEXT PRIMARY KEY, used REAL NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS guest_calls (ticket TEXT PRIMARY KEY, guest TEXT NOT NULL,
                    expires REAL NOT NULL, started REAL, deadline REAL, ended REAL, payload BLOB);
            ''')

    def identify(self, cookie):
        with self.db() as connection:
            # Profiles and provider URLs are transient, including abandoned setup.
            connection.execute('DELETE FROM guest_calls WHERE (started IS NULL AND expires<=?) '
                               'OR ended IS NOT NULL', (time.time(),))
            if self.unlimited and cookie and len(cookie) <= 128:
                connection.execute('INSERT OR IGNORE INTO guests(id) VALUES (?)', (self.hash(cookie),))
                return cookie
            if cookie and len(cookie) <= 128 and connection.execute(
                    'SELECT 1 FROM guests WHERE id=?', (self.hash(cookie),)).fetchone():
                return cookie
            cookie = secrets.token_urlsafe(32)
            connection.execute('INSERT INTO guests(id) VALUES (?)', (self.hash(cookie),))
            return cookie

    @staticmethod
    def hash(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def remaining(self, cookie):
        guest = self.hash(cookie)
        now = time.time()
        with self.db() as connection:
            used = connection.execute('SELECT used FROM guests WHERE id=?', (guest,)).fetchone()[0]
            active = connection.execute('SELECT started, deadline FROM guest_calls WHERE guest=? '
                                        'AND started IS NOT NULL AND ended IS NULL', (guest,)).fetchall()
        return max(0, round(self.seconds - (0 if self.unlimited else used) - sum(max(0, min(now, end) - start) for start, end in active), 3))

    def reserve(self, cookie):
        guest = self.hash(cookie)
        now = time.time()
        with self.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            # A crashed worker's active call is charged through its reserved deadline.
            stale = connection.execute('SELECT ticket, started, deadline FROM guest_calls WHERE '
                                       'guest=? AND ended IS NULL AND deadline<=?', (guest, now)).fetchall()
            for ticket, start, end in stale:
                connection.execute('UPDATE guests SET used=used+? WHERE id=?', (end - start, guest))
                connection.execute('UPDATE guest_calls SET ended=?, payload=NULL WHERE ticket=?', (end, ticket))
            used = connection.execute('SELECT used FROM guests WHERE id=?', (guest,)).fetchone()[0]
            if not self.unlimited and used >= GUEST_SECONDS:
                raise ValueError('Die fünf Minuten zum Ausprobieren sind aufgebraucht. Melden Sie sich an, um weiterzusprechen.')
            busy = connection.execute('SELECT 1 FROM guest_calls WHERE guest=? AND ended IS NULL '
                                      'AND (started IS NOT NULL OR expires>?)', (guest, now)).fetchone()
            if busy:
                raise ValueError('Auf diesem Gerät läuft bereits ein Gespräch oder ein Verbindungsaufbau.')
            ticket = secrets.token_urlsafe(32)
            connection.execute('INSERT INTO guest_calls(ticket,guest,expires) VALUES (?,?,?)',
                               (self.hash(ticket), guest, now + 60))
        return ticket

    def prepare(self, ticket, payload):
        address = urlsplit(payload['signed_url'])
        if (address.scheme != 'wss' or address.hostname != 'api.elevenlabs.io'
                or address.port not in (None, 443) or address.username or address.password
                or address.path != '/v1/convai/conversation' or address.fragment):
            raise ValueError('Invalid voice upstream')
        encrypted = self.cipher.encrypt(json.dumps(payload).encode())
        with self.db() as connection:
            connection.execute('UPDATE guest_calls SET payload=? WHERE ticket=?', (encrypted, self.hash(ticket)))

    def open(self, ticket, cookie):
        now = time.time()
        with self.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT guest, expires, started, ended, payload FROM guest_calls '
                                     'WHERE ticket=?', (self.hash(ticket),)).fetchone()
            if not row or row[0] != self.hash(cookie) or row[1] <= now or row[2] is not None or row[3] is not None or not row[4]:
                raise ValueError('Invalid or expired voice ticket')
            used = connection.execute('SELECT used FROM guests WHERE id=?', (row[0],)).fetchone()[0]
            seconds = max(0, self.seconds - (0 if self.unlimited else used))
            if not seconds:
                raise ValueError('Guest allowance exhausted')
            payload = json.loads(self.cipher.decrypt(row[4]))
            connection.execute('UPDATE guest_calls SET started=?, deadline=?, payload=NULL WHERE ticket=?',
                               (now, now + seconds, self.hash(ticket)))
        return payload, seconds

    def finish(self, ticket):
        now = time.time()
        with self.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT guest, started, deadline, ended FROM guest_calls WHERE ticket=?',
                                     (self.hash(ticket),)).fetchone()
            if not row or row[3] is not None:
                return
            if row[1] is not None:
                elapsed = max(0, min(now, row[2]) - row[1])
                connection.execute('UPDATE guests SET used=MIN(?,used+?) WHERE id=?', (GUEST_SECONDS, elapsed, row[0]))
            connection.execute('UPDATE guest_calls SET ended=?, payload=NULL WHERE ticket=?', (now, self.hash(ticket)))

    def relay(self, client, ticket, cookie, settle, allowed=lambda payload: True, register=lambda payload, resource: None, start=lambda payload: None):
        """Two bounded readers; closing either end always closes the other."""
        upstream = None
        done = Event()
        conversation = [None]
        reader = None
        opened = False
        try:
            payload, seconds = self.open(ticket, cookie)
            opened = True
            if not allowed(payload):
                return
            # The monotonic deadline remains reliable if the system clock changes.
            deadline = time.monotonic() + seconds
            upstream = websocket.create_connection(payload['signed_url'], timeout=10, enable_multithread=True,
                                                   subprotocols=['convai'])
            upstream.settimeout(0.25)

            def receive():
                try:
                    while not done.is_set() and time.monotonic() < deadline and allowed(payload):
                        try:
                            message = upstream.recv()
                        except websocket.WebSocketTimeoutException:
                            continue
                        if not message:
                            break
                        event = json.loads(message)
                        if not isinstance(event, dict):
                            break
                        if event.get('type') == 'conversation_initiation_metadata':
                            conversation[0] = event.get('conversation_initiation_metadata_event', {}).get('conversation_id')
                            register(payload, conversation[0])
                        client.send(message)
                except (OSError, ValueError, ConnectionClosed, websocket.WebSocketException):
                    pass
                finally:
                    done.set()

            reader = Thread(target=receive, daemon=True)
            reader.start()
            initialized = False
            while not done.is_set() and time.monotonic() < deadline and allowed(payload):
                message = client.receive(timeout=0.25)
                if message is None:
                    continue
                event = json.loads(message)
                if not isinstance(event, dict):
                    break
                if event.get('type') == 'conversation_initiation_client_data':
                    if initialized:
                        break
                    initialized = True
                    start(payload)
                    # Bind the validated profile/voice to this ticket.
                    event = {'type': event['type'], 'dynamic_variables': {
                        key: payload[key] for key in ('profiles', 'group_rules', 'greeting')},
                        'conversation_config_override': {'tts': {'voice_id': payload['voice_id']}}}
                    if payload.get('_request'):
                        event['user_id'] = payload['_request']
                if not initialized and event.get('type') != 'conversation_initiation_client_data':
                    break
                # Only supported client events; a browser cannot inject another
                # profile, tool result, session setting or voice override.
                if not (set(event) == {'user_audio_chunk'} and isinstance(event['user_audio_chunk'], str)) and event.get('type') not in {'conversation_initiation_client_data', 'user_audio_chunk', 'pong',
                                             'user_message', 'contextual_update', 'user_activity'}:
                    break
                if not allowed(payload):
                    break
                upstream.send(json.dumps(event))
        except (OSError, ValueError, ConnectionClosed, websocket.WebSocketException):
            pass
        finally:
            done.set()
            if upstream:
                upstream.close(timeout=1)
                upstream.shutdown()
            if reader:
                reader.join(timeout=1)
            if opened:
                self.finish(ticket)
            client.close()
            if opened and conversation[0]:
                settle(conversation[0], payload['reservation'])
