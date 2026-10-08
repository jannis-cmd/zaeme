"""Authenticated /zaeme entry point. The preview gateway stays on loopback.

Run with ZAEME_AUTH_CONFIG pointing to a private JSON file outside the web root.
OAuth tokens are used only to validate sign-in; profiles remain browser-local.
"""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlencode

import requests
from authlib.integrations.flask_client import OAuth
from flask import Flask, Response, abort, g, jsonify, redirect, request, session
from flask_sock import Sock
from threading import Thread
from guest_access import GuestAccess
from security_controls import RequestLimits

ISSUER = 'https://auth.myna-ai.ch'
SESSION_SECONDS = 7 * 24 * 3600
COOKIE = 'zaeme_session'
GUEST_COOKIE = 'zaeme_guest'
API_ROUTES = {'agents/session', 'agents/settle', 'persona', 'chat', 'transcribe', 'speak', 'scribe-token'}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def create_app(config=None):
    if config is None:
        config = json.loads(Path(os.environ['ZAEME_AUTH_CONFIG']).read_text())
    public = urlsplit(config['public_url'])
    prefix = public.path.rstrip('/')
    if public.scheme != 'https' or not public.netloc or prefix != '/zaeme':
        raise ValueError('Expected an HTTPS public URL with /zaeme path.')
    upstream = config.get('upstream', 'http://127.0.0.1:4185').rstrip('/')
    if urlsplit(upstream).hostname != '127.0.0.1':
        raise ValueError('Gateway must be on loopback.')
    app = Flask(__name__, static_folder=None)
    app.config.update(SECRET_KEY=config['cookie_secret'], MAX_CONTENT_LENGTH=5 * 1024 * 1024,
                      SESSION_COOKIE_NAME='zaeme_oidc', SESSION_COOKIE_PATH=prefix + '/',
                      SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax', TRUSTED_HOSTS=[public.netloc])
    database = Path(config['database'])
    database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def db():
        connection = sqlite3.connect(database, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with db() as connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, subject TEXT NOT NULL,
                name TEXT NOT NULL, expires INTEGER NOT NULL);
        ''')
        if 'email' not in {row[1] for row in connection.execute('PRAGMA table_info(sessions)')}:
            connection.execute("ALTER TABLE sessions ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    os.chmod(database, 0o600)
    guests = GuestAccess(db, config['cookie_secret'])
    limits = RequestLimits(db, config['cookie_secret'], config.get('trusted_proxy_cidrs', []))
    app.extensions['zaeme_guests'] = guests
    oauth = OAuth(app)
    provider = oauth.register('zitadel', client_id=config['client_id'],
                              client_secret=config['client_secret'],
                              server_metadata_url=ISSUER + '/.well-known/openid-configuration',
                              client_kwargs={'scope': 'openid profile email',
                                             'code_challenge_method': 'S256',
                                             'token_endpoint_auth_method': 'client_secret_basic',
                                             'timeout': 15})
    app.extensions['zaeme_provider'] = provider

    @app.before_request
    def identify():
        g.csp_nonce = secrets.token_urlsafe(24)
        g.account = None
        g.guest_cookie = None
        client = limits.client(request)
        scope = request.path.removeprefix(prefix)
        maximum = {'/auth/login': 10, '/api/agents/session': 18, '/api/persona': 10,
                   '/api/transcribe': 10, '/api/scribe-token': 6}.get(scope, 60)
        if not limits.allow(client, 'all', 240) or (
                (request.method == 'POST' or scope == '/auth/login' or scope.startswith('/voice/'))
                and not limits.allow(client, '/voice/' if scope.startswith('/voice/') else scope, maximum)):
            response = jsonify(error='Zu viele Anfragen. Bitte in einer Minute nochmals versuchen.')
            response.status_code = 429
            response.headers['Retry-After'] = '60'
            return response
        if scope in ('/', '/index.html', '/auth/session') or request.method == 'POST' or scope.startswith('/voice/'):
            g.guest_cookie = guests.identify(request.cookies.get(GUEST_COOKIE))
        token = request.cookies.get(COOKIE, '')
        if token and len(token) <= 128:
            with db() as connection:
                row = connection.execute('SELECT subject, name, email FROM sessions WHERE token=? AND expires>?',
                                         (digest(token), int(time.time()))).fetchone()
            if row:
                g.account = {'subject': row[0], 'name': row[1], 'email': row[2]}
        if request.method == 'POST':
            # Exact Origin prevents logout/login CSRF and cross-site API usage.
            if request.headers.get('Origin') != public.scheme + '://' + public.netloc:
                abort(403)
            if scope != '/api/transcribe' and (request.content_length or 0) > 32768:
                abort(413)

    @app.after_request
    def secure(response):
        if getattr(g, 'guest_cookie', None) and request.cookies.get(GUEST_COOKIE) != g.guest_cookie:
            response.set_cookie(GUEST_COOKIE, g.guest_cookie, max_age=365 * 24 * 3600,
                                path=prefix + '/', secure=True, httponly=True, samesite='Lax')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        nonce = getattr(g, 'csp_nonce', '')
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
            f"script-src 'self' 'nonce-{nonce}' blob:; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "media-src 'self' blob:; worker-src 'self' blob:; "
            "connect-src 'self' blob: https://api.elevenlabs.io wss://api.elevenlabs.io "
            "https://*.rtc.elevenlabs.io wss://*.rtc.elevenlabs.io "
            "https://*.livekit.cloud wss://*.livekit.cloud; form-action 'self'")
        response.headers['Permissions-Policy'] = 'microphone=(self), camera=(), geolocation=(), payment=()'
        return response

    @app.get(prefix)
    def slash():
        return redirect(prefix + '/')

    @app.get(prefix + '/auth/session')
    def account():
        return jsonify(**runtime())

    @app.get(prefix + '/auth/login')
    def login():
        session.clear()
        try:
            return provider.authorize_redirect(config['public_url'].rstrip('/') + '/auth/callback', ui_locales='de-CH de')
        except requests.RequestException:
            return Response('Die Anmeldung ist gerade nicht erreichbar. Bitte später nochmals versuchen.',
                            status=503, content_type='text/plain; charset=utf-8')

    @app.get(prefix + '/auth/callback')
    def callback():
        try:
            # Authlib validates state, signature, issuer, audience, expiry and nonce.
            token = provider.authorize_access_token()
            user = token['userinfo']
            if user.get('iss') != ISSUER or not user.get('sub'):
                raise ValueError('Missing identity')
            # Code-flow ID tokens may omit email even when the scope is granted.
            if not user.get('email'):
                profile = provider.userinfo(token=token)
                if profile.get('sub') != user['sub']:
                    raise ValueError('Userinfo identity mismatch')
                user = {**user, 'email': profile.get('email', ''),
                        'name': profile.get('name') or user.get('name', '')}
        except Exception:
            session.clear()
            return Response('Die Anmeldung konnte nicht bestätigt werden. Bitte erneut anmelden.',
                            status=400, content_type='text/plain; charset=utf-8')
        session.clear()
        opaque = secrets.token_urlsafe(32)
        with db() as connection:
            connection.execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
            # Replace an existing browser session without changing other devices.
            connection.execute('DELETE FROM sessions WHERE token=?',
                               (digest(request.cookies.get(COOKIE, '')),))
            connection.execute('INSERT INTO sessions (token,subject,name,expires,email) VALUES (?, ?, ?, ?, ?)',
                               (digest(opaque), str(user['sub']), str(user.get('name', ''))[:120],
                                int(time.time()) + SESSION_SECONDS, str(user.get('email', ''))[:320]))
        response = redirect(prefix + '/')
        response.set_cookie(COOKIE, opaque, max_age=SESSION_SECONDS, path=prefix + '/',
                            secure=True, httponly=True, samesite='Lax')
        return response

    @app.post(prefix + '/auth/logout')
    def logout():
        with db() as connection:
            connection.execute('DELETE FROM sessions WHERE token=?',
                               (digest(request.cookies.get(COOKIE, '')),))
        session.clear()
        response = jsonify(authenticated=False, logout_url=ISSUER + '/oidc/v1/end_session?' + urlencode({
            'client_id': config['client_id'], 'post_logout_redirect_uri': config['public_url'].rstrip('/') + '/'}))
        response.delete_cookie(COOKIE, path=prefix + '/', secure=True, httponly=True, samesite='Lax')
        return response

    def runtime():
        return {'enabled': True, 'authenticated': bool(g.account),
                'name': g.account['name'] if g.account else None,
                'email': g.account['email'] if g.account else None,
                # Pseudonymous storage namespace, never raw OAuth identifiers.
                'storage_id': digest(ISSUER + ':' + g.account['subject']) if g.account else None,
                'guest_seconds': None if g.account else guests.remaining(g.guest_cookie)}

    def settle_guest(conversation_id, reservation):
        def attempt():
            for _ in range(6):
                try:
                    result = requests.post(upstream + '/api/agents/settle',
                                           headers={'Host': public.netloc, 'Origin': public.scheme + '://' + public.netloc},
                                           json={'conversation_id': conversation_id, 'reservation': reservation}, timeout=15)
                    if result.ok and result.json().get('settled'):
                        break
                except (requests.RequestException, ValueError):
                    pass
                time.sleep(5)
        Thread(target=attempt, daemon=True).start()

    sock = Sock(app)
    app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25, 'max_message_size': 131072,
                                       'subprotocols': ['convai']}

    @sock.route(prefix + '/voice/<ticket>')
    def guest_voice(ws, ticket):
        if request.headers.get('Origin') != public.scheme + '://' + public.netloc:
            ws.close()
            return
        guests.relay(ws, ticket, g.guest_cookie, settle_guest)

    @app.route(prefix + '/', defaults={'path': ''})
    @app.route(prefix + '/<path:path>', methods=['GET', 'HEAD', 'POST'])
    def gateway(path):
        if any(part in ('.', '..') for part in path.split('/')):
            abort(404)
        if path.startswith('auth/'):
            abort(404)
        if request.method in ('GET', 'HEAD') and path.startswith('api/') and path != 'api/status':
            abort(405)
        if request.method == 'POST':
            if not path.startswith('api/'):
                abort(404)
            route = path.removeprefix('api/')
            if route not in API_ROUTES:
                abort(404)
            if not g.account:
                if route in {'chat', 'speak', 'scribe-token', 'agents/settle'}:
                    return jsonify(error='Bitte starten Sie das Gastgespräch über den Sprechknopf.'), 403
                if route == 'agents/session':
                    data = request.get_json(silent=True)
                    if not isinstance(data, dict) or not isinstance(data.get('profiles'), list) or len(data['profiles']) != 1:
                        return jsonify(error='Ohne Anmeldung kann eine Person am Gespräch teilnehmen.'), 400
                    try:
                        ticket = guests.reserve(g.guest_cookie)
                    except ValueError as exc:
                        return jsonify(error=str(exc)), 429
                else:
                    ticket = None
            else:
                ticket = None
        else:
            ticket = None
        # The gateway is an allowlisted static/API server; no client-selected upstream.
        headers = {'Host': public.netloc, 'Origin': public.scheme + '://' + public.netloc}
        if ticket:
            headers['X-Zaeme-Voice-Transport'] = 'websocket'
        if request.content_type:
            headers['Content-Type'] = request.content_type
        try:
            result = requests.request(request.method, upstream + '/' + path,
                                      headers=headers, data=request.get_data(), timeout=(5, 60),
                                      allow_redirects=False)
        except requests.RequestException:
            if ticket:
                guests.finish(ticket)
            return jsonify(error='Zäme ist gerade nicht erreichbar. Bitte später nochmals versuchen.'), 503
        if ticket:
            try:
                payload = result.json()
                if result.status_code != 200 or payload.get('backend') != 'agents' or not payload.get('signed_url'):
                    guests.finish(ticket)
                    return jsonify(error='Das Gastgespräch ist gerade nicht verfügbar. Bitte später nochmals versuchen.'), 503
                guests.prepare(ticket, payload)
                return jsonify(backend='agents', signed_url='wss://' + public.netloc + prefix + '/voice/' + ticket,
                               profiles=payload['profiles'], group_rules=payload['group_rules'],
                               greeting=payload['greeting'], voice_id=payload['voice_id'],
                               max_seconds=guests.remaining(g.guest_cookie), guest=True)
            except (ValueError, KeyError):
                guests.finish(ticket)
                return jsonify(error='Das Gastgespräch konnte nicht gestartet werden.'), 503
        body = result.content
        content_type = result.headers.get('Content-Type', 'application/octet-stream')
        if path in ('', 'index.html') and result.status_code == 200:
            settings = json.dumps(runtime()).replace('<', '\\u003c')
            body = body.replace(b'</head>', ('<script nonce="' + g.csp_nonce + '">window.ZAEME_AUTH=' + settings +
                                             ';</script></head>').encode())
        return Response(body, status=result.status_code, content_type=content_type)

    return app
