import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agents_service as service


class AgentsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        ledger = patch.object(service, 'LEDGER', Path(folder.name) / 'ledger.json')
        ledger.start()
        self.addCleanup(ledger.stop)

    def recover(self, rows, *, reservations=None, has_more=False, failure=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = Path(folder.name) / 'config.json'
        config.write_text(json.dumps({'agent_id': 'voice', 'persona_agent_id': 'persona'}))
        ledger = {'settled': 20, 'reservations': reservations if reservations is not None else {
            'old': {'created': 1000, 'seconds': 600},
            'recent': {'created': 4900, 'seconds': 600}}}
        with patch.object(service, 'CONFIG', config), patch.object(service.time, 'time', return_value=5000), \
                patch.object(service, 'api', side_effect=failure, return_value={'conversations': rows, 'has_more': has_more}):
            service.reconcile_reservations(ledger)
        return ledger

    def test_ledger_lock_excludes_other_file_handles_until_released(self):
        with service.ledger_lock():
            fd = service.os.open(service.LEDGER.with_suffix('.lock'), service.os.O_WRONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    service.fcntl.flock(fd, service.fcntl.LOCK_EX | service.fcntl.LOCK_NB)
            finally:
                service.os.close(fd)
        with service.ledger_lock():
            pass

    def test_recovery_releases_abandoned_but_not_recent_reservations(self):
        ledger = self.recover([])
        self.assertEqual(set(ledger['reservations']), {'recent'})
        self.assertEqual(ledger['settled'], 20)

    def test_recovery_accounts_overlapping_calls_only_once(self):
        row = {'agent_id': 'voice', 'conversation_id': 'conv_test', 'start_time_unix_secs': 1050,
               'call_duration_secs': 45, 'status': 'done'}
        ledger = self.recover([row], reservations={
            'one': {'created': 1000, 'seconds': 600}, 'two': {'created': 1010, 'seconds': 600}})
        self.assertEqual(ledger['reservations'], {})
        self.assertEqual(ledger['settled'], 65)
        self.assertEqual(ledger['settled_conversations'], ['conv_test'])

    def test_recovery_preserves_active_and_unknown_status_calls(self):
        for status in ('in-progress', 'processing', 'unknown'):
            ledger = self.recover([{'agent_id': 'voice', 'conversation_id': 'conv_test',
                                   'start_time_unix_secs': 1050, 'call_duration_secs': 45, 'status': status}])
            self.assertIn('old', ledger['reservations'])

    def test_recovery_does_not_count_previously_settled_calls_again(self):
        ledger = {'settled': 45, 'settled_conversations': ['conv_test'],
                  'reservations': {'old': {'created': 1000, 'seconds': 600}}}
        with patch.object(service, 'CONFIG') as config, patch.object(service.time, 'time', return_value=5000), \
                patch.object(service, 'api', return_value={'has_more': False, 'conversations': [
                    {'agent_id': 'voice', 'conversation_id': 'conv_test', 'start_time_unix_secs': 1050,
                     'call_duration_secs': 45, 'status': 'done'}]}):
            config.read_text.return_value = json.dumps({'agent_id': 'voice'})
            service.reconcile_reservations(ledger)
        self.assertEqual(ledger['settled'], 45)
        self.assertEqual(ledger['reservations'], {})

    def test_recovery_accounts_for_delayed_start_and_persona_agent(self):
        ledger = self.recover([
            {'agent_id': 'persona', 'conversation_id': 'conv_persona', 'start_time_unix_secs': 1850,
             'call_duration_secs': 15, 'status': 'done'}],
            reservations={'old': {'created': 1000, 'seconds': 60, 'agent_id': 'persona'}})
        self.assertEqual(ledger['settled'], 35)
        self.assertEqual(ledger['reservations'], {})

    def test_recovery_incomplete_or_unavailable_provider_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.recover([], has_more=True)
        with self.assertRaises(RuntimeError):
            self.recover([], failure=RuntimeError('Unavailable'))

    def test_recovery_rejects_nonfinite_duration(self):
        with self.assertRaises(RuntimeError):
            self.recover([{'agent_id': 'voice', 'conversation_id': 'conv_test',
                           'start_time_unix_secs': 1050, 'call_duration_secs': float('nan'), 'status': 'done'}])

    def test_recovery_follows_pagination_before_releasing(self):
        with patch.object(service, 'api', side_effect=[
                {'conversations': [], 'has_more': True, 'next_cursor': 'next'},
                {'conversations': [], 'has_more': False}]) as provider:
            # Keep the shared fixture's provider patch from replacing this one.
            ledger = self.recover([], failure=lambda *args: provider(*args))
        self.assertNotIn('old', ledger['reservations'])
        self.assertIn('cursor=next', provider.call_args_list[1].args[0])

    def test_budget_preserves_reported_high_water_when_analytics_lags(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ledger.json'
            path.write_text(json.dumps({'reset': 1794048910, 'settled': 20,
                                        'reported_high_water': 600, 'reservations': {}}))
            with patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': '20'}), \
                    patch.object(service, 'LEDGER', path), patch.object(service.time, 'time', return_value=1791379200), \
                    patch.object(service, 'api', side_effect=[
                        {'billing_period': 'monthly_period', 'next_character_count_reset_unix': 1794048910},
                        {'columns': ['product_type', 'total_minutes'], 'rows': []}]):
                _, remaining = service.budget()
            self.assertEqual(remaining, 540)

    def test_persona_setup_reuses_provider_secret_without_reading_model_key(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps({'agent_id': 'voice-test'}))
            llm = {'url': 'https://example.com/v1', 'model_id': 'same-model', 'api_key': {'secret_id': 'existing-secret'}}
            with patch.object(service, 'CONFIG', config), \
                    patch.object(service, 'model_api_key', side_effect=AssertionError('Must not export key')), \
                    patch.object(service, 'api', side_effect=[{'conversation_config': {'agent': {'prompt': {'custom_llm': llm}}}}, {'agent_id': 'persona-test'}]) as api:
                service.setup_persona()
            body = api.call_args_list[1].args[1]
            self.assertEqual(body['conversation_config']['agent']['prompt']['custom_llm'], llm)
            self.assertEqual(body['conversation_config']['agent']['prompt']['prompt'], service.PERSONA_RULES)
            self.assertTrue(body['conversation_config']['conversation']['text_only'])
            self.assertTrue(body['platform_settings']['auth']['enable_auth'])
            self.assertFalse(body['platform_settings']['queueing_config']['enabled'])
            self.assertEqual(json.loads(config.read_text())['persona_agent_id'], 'persona-test')

    def test_config_private_same_model_no_burst(self):
        with patch.dict(service.os.environ, {'ZAEME_MODEL_URL': 'https://example.com/openai', 'ZAEME_MODEL_ID': 'same-model'}):
            config = service.agent_config('secret-test')
        self.assertTrue(config['platform_settings']['auth']['enable_auth'])
        self.assertFalse(config['platform_settings']['call_limits']['bursting_enabled'])
        self.assertFalse(config['platform_settings']['queueing_config']['enabled'])
        self.assertEqual(config['conversation_config']['agent']['prompt']['custom_llm']['model_id'], 'same-model')
        self.assertEqual(config['conversation_config']['agent']['prompt']['custom_llm']['url'], 'https://example.com/openai/v1')
        self.assertEqual(config['conversation_config']['conversation']['max_duration_seconds'], 600)
        self.assertTrue(config['platform_settings']['overrides']['conversation_config_override']['tts']['voice_id'])
        self.assertIn('greeting', config['conversation_config']['agent']['dynamic_variables']['dynamic_variable_placeholders'])
        self.assertEqual(config['conversation_config']['turn']['turn_timeout'], 15)
        self.assertEqual(config['conversation_config']['turn']['turn_eagerness'], 'patient')

    def test_low_allowance_falls_back_before_requesting_token(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps({'agent_id': 'test'}))
            with patch.object(service, 'CONFIG', config), patch.object(service, 'budget', return_value=({}, 599)), patch.object(service, 'api') as api:
                result = service.session({'profiles': [{'name': 'Test'}]})
        self.assertEqual(result['backend'], 'classic')
        api.assert_not_called()

    def test_unknown_usage_fails_closed(self):
        with patch.object(service, 'budget', side_effect=RuntimeError('Unavailable')):
            result = service.session({'profiles': [{'name': 'Test'}]})
        self.assertEqual(result['backend'], 'classic')

    def test_bad_voice_rejected(self):
        for voice in ('arbitrary-id', [], {}):
            with self.assertRaises(ValueError):
                service.session({'profiles': [{'name': 'Test'}], 'voice': voice})

    def test_malformed_reservation_rejected_before_reading_secrets(self):
        for reservation in (None, [], {}, 'x' * 129):
            with patch.object(service, 'api') as api, self.assertRaises(ValueError):
                service.settle({'conversation_id': 'conv_synthetic', 'reservation': reservation})
            api.assert_not_called()

    def test_group_session_carries_separate_memories_rules_and_greeting(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps({'agent_id': 'test'}))
            ledger = Path(folder) / 'ledger.json'
            with patch.object(service, 'CONFIG', config), patch.object(service, 'LEDGER', ledger), patch.object(service, 'budget', return_value=({'reservations': {}}, 1200)), patch.object(service, 'api', return_value={'token': 'synthetic'}):
                result = service.session({'profiles': [
                    {'name': 'Hilde', 'guidance': 'Mag Blumen.', 'notes': [{'text': 'Mag gelbe Tulpen.'}]},
                    {'name': 'Ruth', 'guidance': 'Mag Musik.', 'notes': [{'text': 'Mag Jazz.'}]},
                ]})
        profiles = json.loads(result['profiles'])
        self.assertEqual(profiles[0]['notes'], ['Mag gelbe Tulpen.'])
        self.assertEqual(profiles[1]['notes'], ['Mag Jazz.'])
        self.assertEqual(result['group_rules'], service.GROUP_RULES)
        self.assertIn('Hallo Hilde und Ruth.', result['greeting'])

    def test_calendar_period_not_thirty_days(self):
        from datetime import datetime, timezone
        end = int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp())
        start = datetime.fromtimestamp(service.period_start(end), timezone.utc)
        self.assertEqual(start.isoformat(), '2026-10-07T00:00:00+00:00')

    def test_real_provider_product_label_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            def fake_api(path, body=None):
                if path == '/v1/user/subscription':
                    return {'billing_period': 'monthly_period', 'next_character_count_reset_unix': 1794048910}
                return {'columns': ['product_type', 'total_minutes'], 'rows': [['Conversational AI', 10], ['TTS', 200]]}
            with patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': '20'}), patch.object(service, 'LEDGER', Path(folder) / 'ledger.json'), patch.object(service, 'api', side_effect=fake_api), patch.object(service.time, 'time', return_value=1791379200):
                _, remaining = service.budget()
            self.assertEqual(remaining, 540)

    def test_budget_uses_configured_limit_without_subscription_tier(self):
        with tempfile.TemporaryDirectory() as folder:
            def fake_api(path, body=None):
                if path == '/v1/user/subscription':
                    return {'billing_period': 'monthly_period', 'next_character_count_reset_unix': 1794048910}
                return {'columns': ['product_type', 'total_minutes'], 'rows': []}
            with patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': '42'}), patch.object(service, 'LEDGER', Path(folder) / 'ledger.json'), patch.object(service, 'api', side_effect=fake_api), patch.object(service.time, 'time', return_value=1791379200):
                _, remaining = service.budget()
            self.assertEqual(remaining, 42 * 60 - 60)

    def test_external_config_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps({'monthly_agent_minutes': 30}))
            with patch.object(service, 'CONFIG', config), patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': ''}):
                self.assertEqual(service.allowance_seconds(), 1800)
                with patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': '10'}):
                    self.assertEqual(service.allowance_seconds(), 600)

    def test_missing_or_invalid_budget_never_requests_token(self):
        for value in ('', '0', '-2', 'nan', '1.5'):
            with tempfile.TemporaryDirectory() as folder:
                config = Path(folder) / 'config.json'
                config.write_text(json.dumps({'agent_id': 'test'}))
                with patch.object(service, 'CONFIG', config), patch.dict(service.os.environ, {'ZAEME_AGENTS_MONTHLY_MINUTES': value}), patch.object(service, 'api') as api:
                    result = service.session({'profiles': [{'name': 'Test'}]})
                self.assertEqual(result['backend'], 'classic')
                api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
