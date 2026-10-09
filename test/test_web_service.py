import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from joserfc import jwt
from joserfc.jwk import RSAKey

from web_service import ISSUER, create_app
from privacy_store import VERSION, VOICE_NOTICE_VERSION

BASE = 'https://example.com'


class WebServiceTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = dict(public_url=BASE + '/zaeme', client_id='synthetic-client',
                           client_secret='synthetic-secret', cookie_secret='synthetic-cookie-key',
                           invite_only=getattr(self, 'INVITE_ONLY', False),
                           invitation_admin_subjects=['synthetic-admin'],
                           database=str(Path(self.folder.name) / 'auth.sqlite3'))
        self.app = create_app(self.config)
        self.app.testing = True
        self.client = self.app.test_client()
        self.provider = self.app.extensions['zaeme_provider']
        self.key = RSAKey.generate_key(2048)
        self.provider.server_metadata.update(
            _loaded_at=time.time(), issuer=ISSUER, authorization_endpoint=ISSUER + '/authorize',
            token_endpoint=ISSUER + '/token', jwks_uri=ISSUER + '/oauth2/jwks',
            id_token_signing_alg_values_supported=['RS256'])

    def login(self, changes=None):
        response = self.client.get('/zaeme/auth/login', base_url=BASE)
        params = parse_qs(urlsplit(response.location).query)
        self.assertEqual(params['redirect_uri'], [BASE + '/zaeme/auth/callback'])
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertEqual(set(params['scope'][0].split()), {'openid', 'profile', 'email'})
        claims = dict(iss=ISSUER, sub='synthetic-user', aud='synthetic-client',
                      email='test@example.com', email_verified=True, exp=int(time.time()) + 300, iat=int(time.time()), nonce=params['nonce'][0])
        claims.update(changes or {})
        signed = jwt.encode({'alg': 'RS256'}, claims, self.key)
        token = {'access_token': 'synthetic-access', 'id_token': signed, 'token_type': 'Bearer'}
        with patch.object(self.provider, 'fetch_access_token', return_value=token), \
                patch.object(self.provider, 'fetch_jwk_set', return_value={'keys': [self.key.as_dict(private=False)]}):
            return self.client.get('/zaeme/auth/callback?state=' + params['state'][0] + '&code=synthetic', base_url=BASE)

    def book(self, book='synthetic-book'):
        response = self.client.post('/zaeme/privacy/grant', base_url=BASE, headers={'Origin': BASE},
            json={'book': book, 'role': 'fictional', 'version': VERSION, 'accepted': True, 'terms': True})
        self.assertEqual(response.status_code, 200)
        return {'id': book, 'name': 'Fiktiv', 'privacy': response.json}

    def test_signed_oidc_login_and_cookie(self):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        cookies = response.headers.getlist('Set-Cookie')
        cookie = next(value for value in cookies if value.startswith('zaeme_session='))
        for flag in ['Secure', 'HttpOnly', 'SameSite=Lax', 'Path=/zaeme/']:
            self.assertIn(flag, cookie)
        self.assertNotIn('synthetic-access', cookie)
        self.assertTrue(self.client.get('/zaeme/auth/session', base_url=BASE).json['authenticated'])
        self.assertEqual(self.client.get('/zaeme/auth/session', base_url=BASE).json['email'], 'test@example.com')

    def test_rejects_nonce_issuer_audience_and_expiry(self):
        for claims in [{'nonce': 'wrong'}, {'iss': 'https://evil.example'},
                       {'aud': 'other-client'}, {'exp': 1}]:
            with self.subTest(claims=claims):
                self.assertEqual(self.login(claims).status_code, 400)
                self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['authenticated'])

    def test_email_from_userinfo_when_id_token_omits_it(self):
        with patch.object(self.provider, 'userinfo', return_value={
                'sub': 'synthetic-user', 'email': 'profile@example.com'}) as profile:
            self.assertEqual(self.login({'email': None}).status_code, 302)
        profile.assert_called_once()
        self.assertEqual(self.client.get('/zaeme/auth/session', base_url=BASE).json['email'],
                         'profile@example.com')

    def test_provider_profile_cannot_escape_runtime_script(self):
        self.login({'email': '</script><script>alert(1)</script>'})
        upstream = Mock(status_code=200, content=b'<head></head>', headers={'Content-Type': 'text/html'})
        with patch('web_service.requests.request', return_value=upstream):
            response = self.client.get('/zaeme/', base_url=BASE)
        self.assertNotIn(b'</script><script>alert(1)', response.data)
        self.assertIn(b'\\u003c/script>', response.data)

    def test_userinfo_must_match_validated_id_token_subject(self):
        with patch.object(self.provider, 'userinfo', return_value={
                'sub': 'different-user', 'email': 'wrong@example.com'}):
            self.assertEqual(self.login({'email': None}).status_code, 400)
        self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['authenticated'])

    def test_callback_without_state_never_exchanges_token(self):
        with patch.object(self.provider, 'fetch_access_token') as exchange:
            response = self.client.get('/zaeme/auth/callback?code=synthetic', base_url=BASE)
        self.assertEqual(response.status_code, 400)
        exchange.assert_not_called()

    def test_rejects_forged_signature(self):
        response = self.client.get('/zaeme/auth/login', base_url=BASE)
        params = parse_qs(urlsplit(response.location).query)
        attacker = RSAKey.generate_key(2048)
        claims = dict(iss=ISSUER, sub='attacker', aud='synthetic-client',
                      email='test@example.com', exp=int(time.time()) + 300, iat=int(time.time()), nonce=params['nonce'][0])
        token = dict(access_token='synthetic', id_token=jwt.encode({'alg': 'RS256'}, claims, attacker))
        with patch.object(self.provider, 'fetch_access_token', return_value=token), \
                patch.object(self.provider, 'fetch_jwk_set', return_value={'keys': [self.key.as_dict(private=False)]}):
            response = self.client.get('/zaeme/auth/callback?state=' + params['state'][0] + '&code=synthetic', base_url=BASE)
        self.assertEqual(response.status_code, 400)

    def test_path_traversal_cannot_bypass_api_gate(self):
        with patch('web_service.requests.request') as proxy:
            response = self.client.get('/zaeme/foo/../api/status', base_url=BASE)
        self.assertEqual(response.status_code, 404)
        proxy.assert_not_called()

    def test_headers_nonce_and_untrusted_host(self):
        upstream = Mock(status_code=200, content=b'<head></head>', headers={'Content-Type': 'text/html'})
        with patch('web_service.requests.request', return_value=upstream):
            first = self.client.get('/zaeme/', base_url=BASE)
            second = self.client.get('/zaeme/', base_url=BASE)
        csp = first.headers['Content-Security-Policy']
        nonce = csp.split("'nonce-", 1)[1].split("'", 1)[0]
        self.assertIn(('nonce="' + nonce + '"').encode(), first.data)
        self.assertNotEqual(csp, second.headers['Content-Security-Policy'])
        self.assertIn("object-src 'none'", csp)
        self.assertNotIn("script-src 'unsafe-inline'", csp)
        self.assertIn('camera=()', first.headers['Permissions-Policy'])
        self.assertEqual(self.client.get('/zaeme/', base_url='https://evil.example').status_code, 400)

    def test_small_json_body_limit_before_proxy_and_get_method_gate(self):
        with patch('web_service.requests.request') as proxy:
            response = self.client.post('/zaeme/api/persona', base_url=BASE,
                headers={'Origin': BASE}, data=b'x' * 32769, content_type='application/json')
            self.assertEqual(response.status_code, 413)
            self.assertEqual(self.client.get('/zaeme/api/agents/session', base_url=BASE).status_code, 405)
        proxy.assert_not_called()

    def test_durable_burst_limit_cannot_be_reset_with_cookies_or_forwarded_ip(self):
        self.login()
        book = self.book()
        upstream = Mock(status_code=200, content=b'{}', headers={'Content-Type': 'application/json'})
        with patch('web_service.requests.request', return_value=upstream):
            for _ in range(10):
                self.assertEqual(self.client.post('/zaeme/api/persona', base_url=BASE,
                    headers={'Origin': BASE}, json={'profile': book}).status_code, 200)
            restarted = create_app(self.config).test_client()
            cookie = self.client.get_cookie('zaeme_session', domain='example.com', path='/zaeme/')
            restarted.set_cookie('zaeme_session', cookie.value, domain='example.com', path='/zaeme/')
            response = restarted.post('/zaeme/api/persona', base_url=BASE,
                headers={'Origin': BASE, 'X-Forwarded-For': '203.0.113.9'}, json={})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '60')

    def test_static_assets_do_not_allocate_guest_database_rows(self):
        upstream = Mock(status_code=200, content=b'/* asset */', headers={'Content-Type': 'text/javascript'})
        with patch('web_service.requests.request', return_value=upstream), \
                patch.object(self.app.extensions['zaeme_guests'], 'identify') as identify:
            self.client.get('/zaeme/app.js', base_url=BASE)
        identify.assert_not_called()

    def test_every_public_processing_endpoint_requires_login(self):
        with patch('web_service.requests.request') as proxy:
            for route in ['chat', 'speak', 'scribe-token', 'agents/settle', 'persona', 'transcribe', 'agents/session']:
                response = self.client.post('/zaeme/api/' + route, base_url=BASE, headers={'Origin': BASE}, json={})
                self.assertEqual(response.status_code, 401)
            proxy.assert_not_called()

    def test_authenticated_voice_never_exposes_provider_credentials(self):
        self.login()
        book = self.book()
        payload = dict(backend='agents', signed_url='wss://api.elevenlabs.io/v1/convai/conversation?signature=private',
                       reservation='private-reservation', profiles='[]', group_rules='', greeting='Hallo', voice_id='voice')
        upstream = Mock(status_code=200, headers={'Content-Type': 'application/json'})
        upstream.json.return_value = payload
        with patch('web_service.requests.request', return_value=upstream) as proxy:
            response = self.client.post('/zaeme/api/agents/session', base_url=BASE,
                headers={'Origin': BASE}, json={'profiles': [book], 'voice_notice': {'version': VOICE_NOTICE_VERSION, 'confirmed': True}})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(proxy.call_args.kwargs['headers']['X-Zaeme-Voice-Transport'], 'websocket')
            self.assertIn('X-Zaeme-Privacy', proxy.call_args.kwargs['headers'])
            self.assertIn(BASE.replace('https:', 'wss:') + '/zaeme/voice/', response.json['signed_url'])
            self.assertNotIn(b'private', response.data)
            self.assertEqual(self.client.post('/zaeme/api/agents/session', base_url=BASE,
                headers={'Origin': BASE}, json={'profiles': [book], 'voice_notice': {'version': VOICE_NOTICE_VERSION, 'confirmed': True}}).status_code, 429)

    def test_cross_site_and_missing_origin_blocked(self):
        self.login()
        for headers in [{}, {'Origin': 'https://evil.example'}]:
            response = self.client.post('/zaeme/auth/logout', base_url=BASE, headers=headers)
            self.assertEqual(response.status_code, 403)

    def test_logout_revokes_replayed_session(self):
        self.login()
        cookie = self.client.get_cookie('zaeme_session', domain='example.com', path='/zaeme/')
        self.assertEqual(self.client.post('/zaeme/auth/logout', base_url=BASE, headers={'Origin': BASE}).status_code, 200)
        self.client.set_cookie('zaeme_session', cookie.value, domain='example.com', path='/zaeme/')
        self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['authenticated'])

    def test_accounts_have_no_person_or_lifetime_conversation_quota(self):
        self.login()
        books = [self.book('book-' + str(i)) for i in range(15)]
        self.assertEqual(len(self.client.get('/zaeme/privacy/export', base_url=BASE).json['grants']), 15)
        voices = self.app.extensions['zaeme_voices']
        opaque = self.client.get_cookie('zaeme_session', domain='example.com', path='/zaeme/').value
        cookie = voices.identify(opaque)
        # Sequential sessions remain possible after the old five-minute budget.
        with voices.db() as connection:
            connection.execute('UPDATE guests SET used=99999 WHERE id=?', (voices.hash(cookie),))
        ticket = voices.reserve(cookie)
        payload = dict(signed_url='wss://api.elevenlabs.io/v1/convai/conversation?test=1')
        voices.prepare(ticket, payload)
        self.assertEqual(voices.open(ticket, cookie)[1], 600)
        voices.finish(ticket)
        self.assertTrue(voices.reserve(cookie))

    def test_html_runtime_and_private_files(self):
        upstream = Mock(status_code=200, content=b'<head></head>', headers={'Content-Type': 'text/html'})
        with patch('web_service.requests.request', return_value=upstream):
            response = self.client.get('/zaeme/', base_url=BASE)
        self.assertIn(b'"authenticated": false', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertNotIn(b'synthetic-secret', response.data)
        self.assertEqual(self.client.get('/zaeme/auth/config.json', base_url=BASE).status_code, 404)
