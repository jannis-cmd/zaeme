"""App-scoped invitations. Raw bearer links are never persisted."""
import hashlib
import secrets
import time


class InvitationError(ValueError):
    pass


class InvitationStore:
    def __init__(self, db):
        self.db = db
        with db() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS invitations (
                    id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
                    label TEXT NOT NULL, created INTEGER NOT NULL,
                    expires INTEGER NOT NULL, revoked INTEGER,
                    redeemed_subject TEXT, redeemed_at INTEGER);
                CREATE TABLE IF NOT EXISTS invitation_access (
                    subject TEXT PRIMARY KEY, invitation_id TEXT NOT NULL,
                    granted INTEGER NOT NULL, revoked INTEGER);
            ''')

    def create(self, label='', days=7):
        if not isinstance(label, str) or len(label) > 80 or days not in (1, 7, 30):
            raise InvitationError('Bitte eine kurze Bezeichnung und eine gültige Laufzeit wählen.')
        token = secrets.token_urlsafe(32)
        identity = secrets.token_hex(16)
        now = int(time.time())
        with self.db() as connection:
            connection.execute('INSERT INTO invitations (id,token_hash,label,created,expires) VALUES (?,?,?,?,?)',
                               (identity, hashlib.sha256(token.encode()).hexdigest(), label.strip(), now, now + days * 86400))
        return identity, token

    def lookup(self, token):
        if not isinstance(token, str) or len(token) != 43:
            return None
        with self.db() as connection:
            row = connection.execute('SELECT id FROM invitations WHERE token_hash=? AND revoked IS NULL '
                                     'AND redeemed_subject IS NULL AND expires>?',
                                     (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
        return row[0] if row else None

    def pending(self, identity):
        with self.db() as connection:
            return bool(connection.execute('SELECT 1 FROM invitations WHERE id=? AND revoked IS NULL '
                                            'AND redeemed_subject IS NULL AND expires>?',
                                            (identity, int(time.time()))).fetchone())

    def allowed(self, subject):
        with self.db() as connection:
            return bool(connection.execute('SELECT 1 FROM invitation_access WHERE subject=? AND revoked IS NULL',
                                            (subject,)).fetchone())

    def redeem(self, identity, subject):
        now = int(time.time())
        with self.db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            changed = connection.execute('UPDATE invitations SET redeemed_subject=?,redeemed_at=? '
                                         'WHERE id=? AND revoked IS NULL AND redeemed_subject IS NULL AND expires>?',
                                         (subject, now, identity, now)).rowcount
            if changed != 1:
                raise InvitationError('Diese Einladung ist abgelaufen, widerrufen oder bereits verwendet.')
            connection.execute('INSERT INTO invitation_access VALUES (?,?,?,NULL) '
                               'ON CONFLICT(subject) DO UPDATE SET invitation_id=excluded.invitation_id, '
                               'granted=excluded.granted,revoked=NULL', (subject, identity, now))

    def revoke(self, identity):
        now = int(time.time())
        with self.db() as connection:
            connection.execute('UPDATE invitations SET revoked=? WHERE id=? AND revoked IS NULL', (now, identity))
            connection.execute('UPDATE invitation_access SET revoked=? WHERE invitation_id=? AND revoked IS NULL',
                               (now, identity))

    def listing(self):
        with self.db() as connection:
            rows = connection.execute('SELECT id,label,created,expires,revoked,redeemed_at FROM invitations '
                                      'ORDER BY created DESC,id DESC LIMIT 100').fetchall()
        now = int(time.time())
        return [dict(id=r[0], label=r[1] or 'Einladung', expires=r[3],
                     status='Widerrufen' if r[4] is not None else 'Zugang erteilt' if r[5] is not None
                     else 'Abgelaufen' if r[3] <= now else 'Noch nicht verwendet',
                     revoked=r[4] is not None) for r in rows]

    def cleanup(self):
        cutoff = int(time.time()) - 30 * 86400
        with self.db() as connection:
            connection.execute('DELETE FROM invitation_access WHERE revoked IS NOT NULL AND revoked<?', (cutoff,))
            connection.execute('DELETE FROM invitations WHERE (revoked IS NOT NULL AND revoked<?) '
                               'OR (redeemed_subject IS NULL AND expires<?)', (cutoff, cutoff))

    def export(self, subject):
        with self.db() as connection:
            row = connection.execute('SELECT granted,revoked FROM invitation_access WHERE subject=?', (subject,)).fetchone()
        return {'granted_at': row[0], 'revoked_at': row[1]} if row else None
