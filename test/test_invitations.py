import concurrent.futures
import sqlite3
import time
import unittest
import re
from contextlib import closing
from unittest.mock import Mock, patch

from invitation_store import InvitationError
from test import test_web_service as web_tests

BASE = web_tests.BASE


class InvitationTest(unittest.TestCase):
    INVITE_ONLY = True
    setUp = web_tests.WebServiceTest.setUp
    login = web_tests.WebServiceTest.login

    def invite(self, client=None):
        identity, token = self.app.extensions['zaeme_invitations'].create('Test')
        response = (client or self.client).get('/zaeme/invite/' + token, base_url=BASE)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/zaeme/invite')
        return identity, token

    def test_default_is_closed_and_existing_account_is_not_a_grant(self):
        config = {k: v for k, v in self.config.items() if k != 'invite_only'}
        from web_service import create_app
        client = create_app(config).test_client()
        with patch('web_service.requests.request') as proxy:
            self.assertIn('Einladung'.encode(), client.get('/zaeme/', base_url=BASE).data)
            self.assertEqual(client.post('/zaeme/api/agents/session', base_url=BASE,
                                        headers={'Origin': BASE}, json={}).status_code, 401)
            proxy.assert_not_called()
        self.login()
        self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['access_granted'])
        with patch('web_service.requests.request') as proxy:
            self.assertEqual(self.client.post('/zaeme/api/persona', base_url=BASE,
                                             headers={'Origin': BASE}, json={}).status_code, 403)
            self.assertEqual(self.client.get('/zaeme/app.js', base_url=BASE).status_code, 403)
            self.assertEqual(self.client.post('/zaeme/privacy/grant', base_url=BASE,
                                             headers={'Origin': BASE}, json={}).status_code, 403)
            proxy.assert_not_called()

    def test_verified_redemption_survives_login_state_reset_and_is_one_use(self):
        identity, token = self.invite()
        self.assertTrue(self.app.extensions['zaeme_invitations'].pending(identity))
        self.assertEqual(self.login().status_code, 302)
        self.assertTrue(self.client.get('/zaeme/auth/session', base_url=BASE).json['access_granted'])
        self.assertEqual(self.client.get('/zaeme/invite/' + token, base_url=BASE).status_code, 410)
        other = self.app.test_client()
        self.assertEqual(other.get('/zaeme/invite/' + token, base_url=BASE).status_code, 410)
        with closing(sqlite3.connect(self.config['database'])) as connection, connection:
            self.assertNotEqual(connection.execute('SELECT token_hash FROM invitations').fetchone()[0], token)
        with open(self.config['database'], 'rb') as database:
            self.assertNotIn(token.encode(), database.read())

    def test_unverified_identity_cannot_consume_invitation(self):
        identity, _ = self.invite()
        self.assertEqual(self.login({'email_verified': False}).status_code, 403)
        self.assertTrue(self.app.extensions['zaeme_invitations'].pending(identity))
        self.assertFalse(self.app.extensions['zaeme_invitations'].allowed('synthetic-user'))

    def test_userinfo_verification_must_match_signed_identity(self):
        self.invite()
        with patch.object(self.provider, 'userinfo', return_value={
                'sub': 'attacker', 'email': 'test@example.com', 'email_verified': True}):
            self.assertEqual(self.login({'email': None}).status_code, 400)
        self.assertFalse(self.app.extensions['zaeme_invitations'].allowed('synthetic-user'))

    def test_expired_or_revoked_during_login_does_not_grant_access(self):
        identity, _ = self.invite()
        self.app.extensions['zaeme_invitations'].revoke(identity)
        self.assertEqual(self.login().status_code, 403)
        identity, _ = self.invite()
        with closing(sqlite3.connect(self.config['database'])) as connection, connection:
            connection.execute('UPDATE invitations SET expires=? WHERE id=?', (int(time.time()) - 1, identity))
        self.assertEqual(self.login().status_code, 403)

    def test_concurrent_redeemers_only_one_wins(self):
        identity, _ = self.invite()
        store = self.app.extensions['zaeme_invitations']
        def redeem(subject):
            try:
                store.redeem(identity, subject)
                return True
            except InvitationError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(redeem, ['first', 'second'])), 1)

    def test_revocation_blocks_old_session_but_preserves_privacy_rights(self):
        identity, _ = self.invite()
        self.login()
        self.app.extensions['zaeme_invitations'].revoke(identity)
        self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['access_granted'])
        with patch('web_service.requests.request') as proxy:
            self.assertEqual(self.client.post('/zaeme/api/agents/session', base_url=BASE,
                                             headers={'Origin': BASE}, json={}).status_code, 403)
            proxy.assert_not_called()
        self.assertEqual(self.client.get('/zaeme/privacy/export', base_url=BASE).status_code, 200)

    def test_admin_is_subject_bound_and_mutations_require_origin(self):
        self.login()
        self.assertEqual(self.client.get('/zaeme/access', base_url=BASE).status_code, 403)
        self.assertEqual(self.client.post('/zaeme/access/create', base_url=BASE,
                                         headers={'Origin': BASE}, data={'days': '7'}).status_code, 403)
        self.login({'sub': 'synthetic-admin'})
        self.assertTrue(self.client.get('/zaeme/auth/session', base_url=BASE).json['invitation_admin'])
        page = self.client.get('/zaeme/access', base_url=BASE)
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()
        for headers in ({}, {'Origin': 'https://evil.example'}):
            self.assertEqual(self.client.post('/zaeme/access/create', base_url=BASE,
                                             headers=headers, data={'days': '7'}).status_code, 403)
        response = self.client.post('/zaeme/access/create', base_url=BASE, headers={'Origin': BASE},
                                    data={'label': '<script>bad</script>', 'days': '7', 'csrf_token': csrf})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/invite/', response.data)
        self.assertNotIn(b'<script>bad</script>', response.data)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_native_forms_allow_null_origin_only_with_session_bound_token(self):
        self.login({'sub': 'synthetic-admin'})
        page = self.client.get('/zaeme/access', base_url=BASE)
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)[1].decode()
        for headers in ({}, {'Origin': 'null'}, {'Origin': BASE}):
            self.assertEqual(self.client.post('/zaeme/access/create', base_url=BASE, headers=headers,
                                             data={'days': '7', 'csrf_token': csrf}).status_code, 200)
        for headers, token in (({'Origin': 'https://evil.example'}, csrf),
                               ({'Origin': 'null'}, ''), ({'Origin': 'null'}, 'wrong'),
                               ({'Origin': 'null'}, 'ü')):
            self.assertEqual(self.client.post('/zaeme/access/create', base_url=BASE, headers=headers,
                                             data={'days': '7', 'csrf_token': token}).status_code, 403)
        other = self.app.test_client()
        self.assertEqual(other.post('/zaeme/access/create', base_url=BASE, headers={'Origin': 'null'},
                                    data={'days': '7', 'csrf_token': csrf}).status_code, 403)
        identity, _ = self.app.extensions['zaeme_invitations'].create()
        self.assertEqual(self.client.post('/zaeme/access/revoke', base_url=BASE, headers={'Origin': 'null'},
                                         data={'id': identity, 'csrf_token': csrf}).status_code, 303)
        self.assertFalse(self.app.extensions['zaeme_invitations'].pending(identity))

    def test_privacy_pages_stay_public(self):
        upstream = Mock(status_code=200, content=b'legal', headers={'Content-Type': 'text/html'})
        with patch('web_service.requests.request', return_value=upstream):
            self.assertEqual(self.client.get('/zaeme/datenschutz.html', base_url=BASE).status_code, 200)

    def test_malformed_and_unknown_tokens_never_become_pending(self):
        for token in ('short', 'a' * 43, 'a' * 100):
            self.assertEqual(self.client.get('/zaeme/invite/' + token, base_url=BASE).status_code, 410)
        self.assertEqual(self.login().status_code, 302)
        self.assertFalse(self.client.get('/zaeme/auth/session', base_url=BASE).json['access_granted'])

    def test_cleanup_removes_old_revocations_without_restoring_access(self):
        identity, _ = self.invite()
        self.login()
        store = self.app.extensions['zaeme_invitations']
        store.revoke(identity)
        with closing(sqlite3.connect(self.config['database'])) as connection, connection:
            connection.execute('UPDATE invitations SET revoked=?', (int(time.time()) - 31 * 86400,))
            connection.execute('UPDATE invitation_access SET revoked=?', (int(time.time()) - 31 * 86400,))
        store.cleanup()
        self.assertFalse(store.allowed('synthetic-user'))
        self.assertEqual(store.listing(), [])
        self.assertIsNone(store.export('synthetic-user'))
