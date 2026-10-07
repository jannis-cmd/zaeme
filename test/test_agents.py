import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agents_service as service


class AgentsTest(unittest.TestCase):
    def test_config_private_same_model_no_burst(self):
        with patch.dict(service.os.environ, {'ZAEME_MODEL_URL': 'https://example.com/openai', 'ZAEME_MODEL_ID': 'same-model'}):
            config = service.agent_config('secret-test')
        self.assertTrue(config['platform_settings']['auth']['enable_auth'])
        self.assertFalse(config['platform_settings']['call_limits']['bursting_enabled'])
        self.assertEqual(config['conversation_config']['agent']['prompt']['custom_llm']['model_id'], 'same-model')
        self.assertEqual(config['conversation_config']['agent']['prompt']['custom_llm']['url'], 'https://example.com/openai/v1')
        self.assertEqual(config['conversation_config']['conversation']['max_duration_seconds'], 600)
        self.assertTrue(config['platform_settings']['overrides']['conversation_config_override']['tts']['voice_id'])

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
        with self.assertRaises(ValueError):
            service.session({'profiles': [{'name': 'Test'}], 'voice': 'arbitrary-id'})

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
