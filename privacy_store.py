"""Minimal consent receipts and provider deletion queue; never profile contents.

The authenticated service owns grants. The loopback gateway receives a signed
context and rechecks it before sending profile data to a provider.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

VERSION = '2026-10-09.1'
BOOK_ID = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
CONVERSATION_ID = re.compile(r'^conv_[A-Za-z0-9_]{1,120}$')
ROLES = {'self', 'representative', 'fictional'}


class PrivacyError(ValueError):
    pass


class PrivacyStore:
    def __init__(self, database, secret):
        self.database = Path(database)
        self.secret = secret.encode()
        with self.db() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS privacy_grants (
                    owner TEXT NOT NULL, book TEXT NOT NULL, receipt TEXT NOT NULL,
                    version TEXT NOT NULL, role TEXT NOT NULL, authority TEXT NOT NULL,
                    granted INTEGER NOT NULL, revoked INTEGER,
                    PRIMARY KEY (owner, book));
                CREATE TABLE IF NOT EXISTS privacy_events (
                    id INTEGER PRIMARY KEY, owner TEXT NOT NULL, book TEXT NOT NULL,
                    action TEXT NOT NULL, version TEXT NOT NULL, role TEXT NOT NULL,
                    authority TEXT NOT NULL, happened INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS privacy_requests (
                    request TEXT PRIMARY KEY, owner TEXT NOT NULL, books TEXT NOT NULL,
                    created INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'prepared');
                CREATE TABLE IF NOT EXISTS privacy_resources (
                    resource TEXT PRIMARY KEY, owner TEXT NOT NULL, books TEXT NOT NULL,
                    created INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                    attempts INTEGER NOT NULL DEFAULT 0, next_attempt INTEGER NOT NULL DEFAULT 0);
            ''')
            if 'last_checked' not in {row[1] for row in connection.execute('PRAGMA table_info(privacy_requests)')}:
                connection.execute('ALTER TABLE privacy_requests ADD COLUMN last_checked INTEGER NOT NULL DEFAULT 0')
        os.chmod(self.database, 0o600)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def owner(self, subject):
        return hmac.new(self.secret, ('privacy:' + subject).encode(), hashlib.sha256).hexdigest()

    def grant(self, owner, data, real_allowed=False):
        book, role = data.get('book'), data.get('role')
        authority = data.get('authority', '')
        if not isinstance(book, str) or not BOOK_ID.fullmatch(book) or not isinstance(role, str) or role not in ROLES:
            raise PrivacyError('Bitte Person und Freigabeart prüfen.')
        if data.get('version') != VERSION or data.get('accepted') is not True or data.get('terms') is not True:
            raise PrivacyError('Bitte die aktuelle Information lesen und ausdrücklich zustimmen.')
        if role != 'fictional' and not real_allowed:
            raise PrivacyError('Echte Profile sind für dieses Konto noch nicht freigegeben. Bitte nur erfundene Angaben verwenden.')
        if role == 'representative' and (not isinstance(authority, str) or authority not in {'mandate', 'deputy', 'other'}):
            raise PrivacyError('Bitte die tatsächliche Vertretungsbefugnis angeben. Angehörigenstatus allein genügt nicht.')
        authority = authority if role == 'representative' else ''
        receipt = secrets.token_urlsafe(32)
        now = int(time.time())
        with self.db() as connection:
            connection.execute('INSERT INTO privacy_grants VALUES (?,?,?,?,?,?,?,NULL) '
                               'ON CONFLICT(owner,book) DO UPDATE SET receipt=excluded.receipt, '
                               'version=excluded.version,role=excluded.role,authority=excluded.authority, '
                               'granted=excluded.granted,revoked=NULL',
                               (owner, book, receipt, VERSION, role, authority, now))
            connection.execute('INSERT INTO privacy_events(owner,book,action,version,role,authority,happened) '
                               'VALUES (?,?,?,?,?,?,?)', (owner, book, 'grant', VERSION, role, authority, now))
        return {'book': book, 'receipt': receipt, 'version': VERSION, 'role': role,
                'authority': authority, 'granted': now}

    def validate(self, owner, profiles, real_allowed=False):
        if not isinstance(profiles, list) or not profiles or len(profiles) > 100:
            raise PrivacyError('Bitte mindestens ein freigegebenes Freundschaftsbuch auswählen.')
        books = []
        with self.db() as connection:
            for profile in profiles:
                if not isinstance(profile, dict):
                    raise PrivacyError('Ungültiges Freundschaftsbuch.')
                book = profile.get('id')
                receipt = (profile.get('privacy') or {}).get('receipt') if isinstance(profile.get('privacy', {}), dict) else None
                if not isinstance(book, str) or not isinstance(receipt, str):
                    raise PrivacyError('Für dieses Freundschaftsbuch fehlt die Freigabe.')
                row = connection.execute('SELECT * FROM privacy_grants WHERE owner=? AND book=?', (owner, book)).fetchone()
                if (not row or row['revoked'] is not None or row['version'] != VERSION
                        or not hmac.compare_digest(row['receipt'].encode(), receipt.encode())
                        or (row['role'] != 'fictional' and not real_allowed)):
                    raise PrivacyError('Die Freigabe fehlt, wurde widerrufen oder muss erneuert werden.')
                books.append({'id': book, 'privacy': {'receipt': receipt}})
        if len({book['id'] for book in books}) != len(books):
            raise PrivacyError('Ein Freundschaftsbuch wurde mehrfach ausgewählt.')
        return books

    def active(self, owner, books, real_allowed=False):
        try:
            self.validate(owner, books, real_allowed)
            return True
        except PrivacyError:
            return False

    def revoke(self, owner, book, delete=False):
        if not isinstance(book, str) or not BOOK_ID.fullmatch(book):
            raise PrivacyError('Ungültiges Freundschaftsbuch.')
        with self.db() as connection:
            row = connection.execute('SELECT * FROM privacy_grants WHERE owner=? AND book=?', (owner, book)).fetchone()
            if row and row['revoked'] is None:
                connection.execute('UPDATE privacy_grants SET revoked=? WHERE owner=? AND book=?',
                                   (int(time.time()), owner, book))
                connection.execute('INSERT INTO privacy_events(owner,book,action,version,role,authority,happened) '
                                   'VALUES (?,?,?,?,?,?,?)', (owner, book, 'delete' if delete else 'revoke',
                                   row['version'], row['role'], row['authority'], int(time.time())))
            # Shared conversations must be deleted as a whole; don't retain a
            # revoked person's contributions in another participant's history.
            for resource in connection.execute('SELECT resource,books FROM privacy_resources WHERE owner=?', (owner,)).fetchall():
                if book in json.loads(resource['books']):
                    connection.execute("UPDATE privacy_resources SET status='pending',next_attempt=0 WHERE resource=?", (resource['resource'],))
            # The tombstone blocks old clients/receipts. Minimal receipt history
            # is retained for 90 days for rights handling and restoration checks.
        return {'revoked': True, 'provider_deletion': 'queued', 'local_deletion_required': True}

    def prepare_request(self, owner, books):
        correlation = secrets.token_urlsafe(24)
        with self.db() as connection:
            connection.execute('INSERT INTO privacy_requests(request,owner,books,created) VALUES (?,?,?,?)',
                               (correlation, owner, json.dumps(books), int(time.time())))
        return correlation

    def start_request(self, correlation):
        with self.db() as connection:
            connection.execute("UPDATE privacy_requests SET status='open' WHERE request=? AND status='prepared'", (correlation,))

    def register(self, owner, books, resource, correlation=None):
        if not isinstance(resource, str) or not CONVERSATION_ID.fullmatch(resource):
            raise PrivacyError('Ungültige Anbieterkennung.')
        ids = [book['id'] for book in books]
        with self.db() as connection:
            # Registration and revocation serialize through SQLite. A late
            # provider response after withdrawal must still enter the queue.
            connection.execute('BEGIN IMMEDIATE')
            active = all(connection.execute('SELECT 1 FROM privacy_grants WHERE owner=? AND book=? '
                                            'AND receipt=? AND revoked IS NULL AND version=?',
                                            (owner, book['id'], book['privacy']['receipt'], VERSION)).fetchone() for book in books)
            existing = connection.execute('SELECT owner,books FROM privacy_resources WHERE resource=?', (resource,)).fetchone()
            if existing and (existing['owner'] != owner or json.loads(existing['books']) != ids):
                raise PrivacyError('Anbieterkennung ist bereits einem anderen Vorgang zugeordnet.')
            if correlation:
                connection.execute("UPDATE privacy_requests SET status='resolved' WHERE request=? AND owner=?", (correlation, owner))
            connection.execute('INSERT OR IGNORE INTO privacy_resources(resource,owner,books,created,status) VALUES (?,?,?,?,?)',
                               (resource, owner, json.dumps(ids), int(time.time()), 'active' if active else 'pending'))

    def export(self, owner):
        with self.db() as connection:
            return {'version': VERSION,
                    'grants': [dict(row) for row in connection.execute(
                        'SELECT book,version,role,authority,granted,revoked FROM privacy_grants WHERE owner=?', (owner,))],
                    'events': [dict(row) for row in connection.execute(
                        'SELECT book,action,version,role,authority,happened FROM privacy_events WHERE owner=? ORDER BY id', (owner,))],
                    'provider_records': [dict(row) for row in connection.execute(
                        'SELECT resource,books,created,status FROM privacy_resources WHERE owner=?', (owner,))]}

    def sign_context(self, owner, books, real_allowed, session_token, correlation):
        body = base64.urlsafe_b64encode(json.dumps({'owner': owner, 'books': books, 'real_allowed': real_allowed,
                                                   'request': correlation, 'session': session_token, 'expires': int(time.time()) + 120}).encode()).decode()
        return body + '.' + hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()

    def context_active(self, context):
        with self.db() as connection:
            valid = connection.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',
                                       (context['session'], int(time.time()))).fetchone()
        return bool(valid and context['expires'] >= time.time() and
                    self.active(context['owner'], context['books'], context['real_allowed']))

    def verify_context(self, value):
        try:
            body, signature = value.rsplit('.', 1)
            if not hmac.compare_digest(signature, hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()):
                raise ValueError()
            context = json.loads(base64.urlsafe_b64decode(body))
            if not self.context_active(context):
                raise ValueError()
            return context
        except (ValueError, KeyError, TypeError):
            raise PrivacyError('Die Datenfreigabe ist nicht mehr gültig.') from None

    def cleanup(self):
        """Run daily. Pending deletions are never silently pruned."""
        cutoff = int(time.time()) - 90 * 86400
        with self.db() as connection:
            connection.execute("UPDATE privacy_resources SET status='pending' WHERE status='active' AND created<?", (int(time.time()) - 86400,))
            connection.execute("DELETE FROM privacy_requests WHERE status='prepared' AND created<?", (int(time.time()) - 86400,))
            connection.execute("DELETE FROM privacy_requests WHERE status='resolved' AND created<?", (cutoff,))
            connection.execute('DELETE FROM privacy_events WHERE happened<?', (cutoff,))
            connection.execute("DELETE FROM privacy_resources WHERE created<? AND status='deleted'", (cutoff,))
            connection.execute('DELETE FROM privacy_grants WHERE revoked<? AND NOT EXISTS '
                               '(SELECT 1 FROM privacy_resources r WHERE r.owner=privacy_grants.owner '
                               "AND r.status!='deleted' AND EXISTS (SELECT 1 FROM json_each(r.books) WHERE value=privacy_grants.book)) "
                               'AND NOT EXISTS (SELECT 1 FROM privacy_requests q WHERE q.owner=privacy_grants.owner '
                               "AND q.status='open' AND EXISTS (SELECT 1 FROM json_each(q.books) WHERE json_extract(value,'$.id')=privacy_grants.book))", (cutoff,))


def upstream_context(value):
    if not value:
        if os.environ.get('ZAEME_AUTH_CONFIG'):
            raise PrivacyError('Signierter interner Datenschutzkontext fehlt.')
        return None, None
    config = json.loads(Path(os.environ['ZAEME_AUTH_CONFIG']).read_text())
    store = PrivacyStore(config['database'], config['cookie_secret'])
    return store, store.verify_context(value)
