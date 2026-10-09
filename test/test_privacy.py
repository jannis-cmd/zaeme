import json
import os
import time
import unittest
from unittest.mock import Mock, patch

from test import test_web_service
from privacy_store import VERSION, VOICE_NOTICE_VERSION, PrivacyError, upstream_context, real_profiles_allowed
from privacy_admin import drain, revoke_user, reconcile_requests, health
from web_service import digest

BASE = test_web_service.BASE

class PrivacyTest(unittest.TestCase):
    setUp = test_web_service.WebServiceTest.setUp
    login = test_web_service.WebServiceTest.login
    book = test_web_service.WebServiceTest.book

    def post(self, path, data):
        return self.client.post('/zaeme/' + path, base_url=BASE, headers={'Origin': BASE}, json=data)

    def test_public_release_requires_every_operator_gate_and_known_access_mode(self):
        settings = dict(real_profiles_access='public', real_profiles_enabled=True,
                        provider_contracts_confirmed=True, risk_review_approved=True)
        self.assertTrue(real_profiles_allowed({'privacy': settings}, 'new-account'))
        for key in ('real_profiles_enabled', 'provider_contracts_confirmed', 'risk_review_approved'):
            for invalid in (False, None, 'true', 1):
                self.assertFalse(real_profiles_allowed({'privacy': {**settings, key: invalid}}, 'new-account'))
        self.assertFalse(real_profiles_allowed({'privacy': {**settings, 'real_profiles_access': 'typo'}}, 'new-account'))
        self.assertFalse(real_profiles_allowed({'privacy': {**settings, 'real_profiles_access': 'restricted'}}, 'new-account'))
        self.assertFalse(real_profiles_allowed({'privacy': None}, 'new-account'))
        self.assertFalse(real_profiles_allowed({'privacy': settings}, None))

    def test_voice_notice_is_required_before_any_provider_request(self):
        self.login()
        book = self.book()
        with patch('web_service.requests.request') as proxy:
            for notice in (None, {}, {'version': 'old', 'confirmed': True},
                           {'version': VOICE_NOTICE_VERSION, 'confirmed': 'true'},
                           {'version': VOICE_NOTICE_VERSION, 'confirmed': False}):
                self.assertEqual(self.post('api/agents/session', {'profiles': [book], 'voice_notice': notice}).status_code, 403)
            proxy.assert_not_called()

    def test_voice_notice_export_is_owner_bound_and_contains_no_receipts(self):
        self.login()
        store = self.app.extensions['zaeme_privacy']
        book = self.book()
        owner = store.owner('synthetic-user')
        store.prepare_request(owner, [book], {'version': VOICE_NOTICE_VERSION, 'confirmed': True})
        notices = store.export(owner)['voice_notices']
        self.assertEqual(notices[0]['books'], [book['id']])
        self.assertNotIn('receipt', json.dumps(notices))
        self.assertEqual(store.export(store.owner('other-account'))['voice_notices'], [])

    def test_privacy_health_detects_missing_stale_worker_and_unresolved_calls(self):
        store = self.app.extensions['zaeme_privacy']
        self.assertFalse(health(store)['healthy'])
        drain(store, delete=lambda _: None, discover=lambda _: [])
        self.assertTrue(health(store)['healthy'])
        self.assertFalse(health(store, now=int(time.time()) + 901)['healthy'])
        correlation = store.prepare_request('synthetic', [])
        store.start_request(correlation)
        with store.db() as db:
            db.execute('UPDATE privacy_requests SET created=? WHERE request=?', (int(time.time()) - 86401, correlation))
        status = health(store)
        self.assertEqual(status['overdue_discoveries'], 1)
        self.assertFalse(status['healthy'])

    def test_empty_discoveries_do_not_starve_later_requests(self):
        store = self.app.extensions['zaeme_privacy']
        requests = [store.prepare_request('synthetic', []) for _ in range(51)]
        for correlation in requests:
            store.start_request(correlation)
        checked = []
        def discover(correlation):
            checked.append(correlation)
            return []
        reconcile_requests(store, discover)
        reconcile_requests(store, discover)
        self.assertEqual(set(checked), set(requests))

    def test_grant_requires_login_explicit_information_and_separate_terms(self):
        data = dict(book='book', role='fictional', version=VERSION, accepted=True, terms=True)
        self.assertEqual(self.post('privacy/grant', data).status_code, 401)
        self.login()
        for invalid in [dict(data, accepted=False), dict(data, terms=False), dict(data, version='old'), dict(data, role=[])]:
            self.assertEqual(self.post('privacy/grant', invalid).status_code, 403)
        self.assertEqual(self.post('privacy/grant', data).status_code, 200)
        export = self.client.get('/zaeme/privacy/export', base_url=BASE).json
        self.assertNotIn('receipt', export['grants'][0])
        self.assertNotIn('email', json.dumps(export))

    def test_real_profile_requires_all_operator_gates_and_approved_account(self):
        self.login()
        data = dict(book='book', role='self', version=VERSION, accepted=True, terms=True)
        settings = self.config['privacy'] = dict(real_profiles_enabled=True, provider_contracts_confirmed=True,
                                                risk_review_approved=True, approved_subjects=['synthetic-user'])
        for missing in ['real_profiles_enabled', 'provider_contracts_confirmed', 'risk_review_approved']:
            settings[missing] = False
            self.assertEqual(self.post('privacy/grant', data).status_code, 403)
            settings[missing] = True
        settings['approved_subjects'] = ['other']
        self.assertEqual(self.post('privacy/grant', data).status_code, 403)
        settings['approved_subjects'] = ['synthetic-user']
        self.assertEqual(self.post('privacy/grant', data).status_code, 200)
        self.assertEqual(self.post('privacy/grant', dict(data, role='representative')).status_code, 403)
        self.assertEqual(self.post('privacy/grant', dict(data, role='representative', authority='deputy')).status_code, 200)

    def test_missing_forged_other_book_and_other_account_grants_never_reach_provider(self):
        self.login()
        book = self.book()
        with patch('web_service.requests.request') as proxy:
            for profile in [{}, {'id': 'other', 'privacy': book['privacy']},
                            dict(book, privacy={'receipt': 'forged'}), dict(book, privacy={'receipt': 'é'})]:
                self.assertEqual(self.post('api/persona', {'profile': profile}).status_code, 403)
            self.login({'sub': 'other-user'})
            self.assertEqual(self.post('api/persona', {'profile': book}).status_code, 403)
            proxy.assert_not_called()

    def test_all_group_members_must_have_valid_grants(self):
        self.login()
        book = self.book()
        with patch('web_service.requests.request') as proxy:
            self.assertEqual(self.post('api/agents/session', {'profiles': [book, {'id': 'missing'}]}).status_code, 403)
            proxy.assert_not_called()

    def test_old_receipt_stays_invalid_after_regrant(self):
        self.login()
        original = self.book()
        self.assertEqual(self.post('privacy/revoke', {'book': original['id']}).status_code, 200)
        new = self.book()
        store = self.app.extensions['zaeme_privacy']
        with self.assertRaises(PrivacyError):
            store.validate(store.owner('synthetic-user'), [original])
        self.assertTrue(store.active(store.owner('synthetic-user'), [new]))

    def test_withdrawal_queues_whole_group_and_late_metadata_for_deletion(self):
        self.login()
        books = [self.book('one'), self.book('two')]
        store = self.app.extensions['zaeme_privacy']
        owner = store.owner('synthetic-user')
        store.register(owner, books, 'conv_group')
        self.post('privacy/revoke', {'book': 'one'})
        store.register(owner, books, 'conv_late')
        resources = store.export(owner)['provider_records']
        self.assertEqual({row['status'] for row in resources}, {'pending'})
        deleted = []
        result = drain(store, delete=deleted.append, discover=lambda _: [])
        self.assertEqual(result['completed'], 2)
        self.assertCountEqual(deleted, ['conv_group', 'conv_late'])
        self.assertEqual({row['status'] for row in store.export(owner)['provider_records']}, {'deleted'})

    def test_lost_metadata_is_recovered_via_durable_random_request_correlation(self):
        self.login()
        book = self.book()
        store = self.app.extensions['zaeme_privacy']
        owner = store.owner('synthetic-user')
        correlation = store.prepare_request(owner, [book])
        store.start_request(correlation)
        self.post('privacy/revoke', {'book': book['id']})
        deleted = []
        def discover(value):
            self.assertEqual(value, correlation)
            self.assertNotIn('synthetic-user', value)
            return ['conv_recovered']
        result = drain(store, delete=deleted.append, discover=discover)
        self.assertEqual(deleted, ['conv_recovered'])
        self.assertEqual(result['unresolved_requests'], 0)

    def test_failed_delete_is_retained_and_retried_not_reported_as_deleted(self):
        self.login()
        book = self.book()
        store = self.app.extensions['zaeme_privacy']
        owner = store.owner('synthetic-user')
        store.register(owner, [book], 'conv_failure')
        self.post('privacy/delete', {'book': book['id']})
        def fail(_):
            raise RuntimeError('synthetic confidential provider body')
        result = drain(store, delete=fail, discover=lambda _: [])
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['pending'], 1)
        with store.db() as connection:
            row = dict(connection.execute('SELECT * FROM privacy_resources').fetchone())
        self.assertEqual(row['status'], 'pending')
        self.assertGreater(row['next_attempt'], time.time())
        self.assertNotIn('confidential', json.dumps(row))

    def test_retention_preserves_open_requests_and_their_revoked_receipts(self):
        self.login()
        book = self.book()
        store = self.app.extensions['zaeme_privacy']
        owner = store.owner('synthetic-user')
        correlation = store.prepare_request(owner, [book])
        store.start_request(correlation)
        self.post('privacy/revoke', {'book': book['id']})
        with store.db() as connection:
            connection.execute('UPDATE privacy_grants SET revoked=1')
        store.cleanup()
        self.assertEqual(len(store.export(owner)['grants']), 1)

    def test_logout_all_blocks_inflight_persona_result_and_future_requests(self):
        self.login()
        book = self.book()
        store = self.app.extensions['zaeme_privacy']
        def upstream(*args, **kwargs):
            revoke_user(store, 'synthetic-user')
            return Mock(status_code=200, content=b'{"summary":"must not escape"}', headers={'Content-Type':'application/json'})
        with patch('web_service.requests.request', side_effect=upstream):
            response = self.post('api/persona', {'profile': book})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b'must not escape', response.data)
        self.assertEqual(self.post('api/persona', {'profile': book}).status_code, 401)

    def test_signed_context_is_expiring_and_session_bound_and_gateway_fails_closed(self):
        self.login()
        book = self.book()
        store = self.app.extensions['zaeme_privacy']
        owner = store.owner('synthetic-user')
        opaque = self.client.get_cookie('zaeme_session', domain='example.com', path='/zaeme/').value
        value = store.sign_context(owner, [book], False, digest(opaque), store.prepare_request(owner, [book]))
        self.assertEqual(store.verify_context(value)['owner'], owner)
        with self.assertRaises(PrivacyError): store.verify_context(value + 'x')
        with patch.dict(os.environ, {'ZAEME_AUTH_CONFIG':'/synthetic/private/auth.json'}):
            with self.assertRaises(PrivacyError): upstream_context(None)
        self.post('privacy/logout-all', {})
        with self.assertRaises(PrivacyError): store.verify_context(value)

    def test_separate_voice_paths_are_disabled_even_for_signed_in_accounts(self):
        self.login()
        with patch('web_service.requests.request') as proxy:
            for route in ['chat','speak','scribe-token','transcribe']:
                self.assertEqual(self.post('api/' + route, {}).status_code, 410)
            proxy.assert_not_called()
