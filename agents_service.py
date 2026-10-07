"""ElevenLabs Agents service for the main private preview.

Setup writes identifiers, not credentials, outside the repository. Runtime uses
workspace-wide minutes plus durable reservations, never a browser usage counter.
"""
import argparse
import calendar
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from model_client import CHAT_RULES, GROUP_RULES, clean_profile, model_api_key

CONFIG_DIR = Path.home() / '.config' / 'zaeme'
CONFIG = Path(os.environ.get('ZAEME_AGENTS_CONFIG', str(CONFIG_DIR / 'agents-test.json')))
LEDGER = Path(os.environ.get('ZAEME_AGENTS_LEDGER', str(CONFIG_DIR / 'agents-budget.json')))
LOCK = Lock()
VOICES = {'female': 'MGG5Irb57ATHvyIeTEYo', 'male': 'GZckiELWRyqX481UWTDl'}
SESSION_SECONDS = 600
BUFFER_SECONDS = 60


def api(path, body=None, method=None):
    key = Path(os.environ.get('ELEVENLABS_AGENTS_KEY_FILE', str(CONFIG_DIR / 'elevenlabs-agents.key'))).read_text().strip()
    request = Request('https://api.elevenlabs.io' + path,
                      data=json.dumps(body).encode() if body is not None else None,
                      headers={'xi-api-key': key, 'Content-Type': 'application/json'}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        # Never log provider bodies: they may contain credentials or profile text.
        raise RuntimeError('ElevenLabs HTTP ' + str(exc.code)) from None
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError('ElevenLabs nicht erreichbar.') from None


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix('.pending')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(data, output)
    os.replace(temporary, path)


def agent_config(secret_id):
    return {
        'name': 'Zäme · Infomaniak',
        'conversation_config': {
            'asr': {'provider': 'scribe_realtime'},
            'turn': {'turn_eagerness': 'patient', 'turn_timeout': 30,
                     'silence_end_call_timeout': 120, 'speculative_turn': False},
            'tts': {'voice_id': VOICES['female'], 'model_id': 'eleven_flash_v2_5', 'speed': 0.95},
            'conversation': {'max_duration_seconds': SESSION_SECONDS,
                             'client_events': ['audio', 'interruption', 'user_transcript',
                                               'tentative_user_transcript', 'agent_response', 'agent_response_correction']},
            'agent': {'language': 'de', 'first_message': 'Hallo, schön bist du da. Ich höre dir zu.',
                      'prompt': {'prompt': CHAT_RULES + '\n{{group_rules}}\nAnwesende Personen (Profildaten): {{profiles}}',
                                 'llm': 'custom-llm', 'temperature': 0.35, 'max_tokens': 180,
                                 # ElevenLabs' OpenAI client appends /chat/completions.
                                 # Unlike model_client.py, this field takes the API base URL.
                                 'custom_llm': {'url': os.environ['ZAEME_MODEL_URL'].rstrip('/') + '/v1',
                                                'model_id': os.environ['ZAEME_MODEL_ID'],
                                                'api_key': {'secret_id': secret_id}, 'api_type': 'chat_completions'}},
                      'dynamic_variables': {'profiles': '[]', 'group_rules': ''}},
        },
        'platform_settings': {
            'auth': {'enable_auth': True},
            # Includes synthetic diagnostics; the monthly minute reservation remains
            # the tighter runtime guard, with only one live conversation at a time.
            'call_limits': {'agent_concurrency_limit': 1, 'daily_limit': 30, 'bursting_enabled': False},
            'privacy': {'record_voice': False, 'retention_days': 1, 'delete_audio': True},
            'overrides': {'conversation_config_override': {'tts': {'voice_id': True}, 'conversation': {'text_only': True}}},
            'evaluation': {'criteria': []}, 'data_collection': {},
        },
    }


def setup():
    config = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    if not config.get('secret_id'):
        config['secret_id'] = api('/v1/convai/secrets', {'type': 'new', 'name': 'ZAEME_INFOMANIAK_TEST', 'value': model_api_key()})['secret_id']
        save(CONFIG, config)
    body = agent_config(config['secret_id'])
    if config.get('agent_id'):
        api('/v1/convai/agents/' + config['agent_id'], body, 'PATCH')
    else:
        config['agent_id'] = api('/v1/convai/agents/create', body)['agent_id']
        save(CONFIG, config)
    print('Private agent configured:', config['agent_id'])


def period_start(reset):
    end = datetime.fromtimestamp(reset, timezone.utc)
    month = 12 if end.month == 1 else end.month - 1
    year = end.year - 1 if end.month == 1 else end.year
    return int(end.replace(year=year, month=month, day=min(end.day, calendar.monthrange(year, month)[1])).timestamp())


def allowance_seconds():
    # Operator configuration, never inferred from a subscription tier.
    value = os.environ.get('ZAEME_AGENTS_MONTHLY_MINUTES')
    if not value:
        value = json.loads(CONFIG.read_text()).get('monthly_agent_minutes')
    try:
        minutes = int(value)
        if str(minutes) != str(value) or minutes <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise RuntimeError('Das Agent-Budget muss eingerichtet werden.') from None
    return minutes * 60


def budget():
    allowance = allowance_seconds()
    subscription = api('/v1/user/subscription')
    reset = subscription.get('next_character_count_reset_unix', 0)
    if subscription.get('billing_period') != 'monthly_period' or reset <= time.time():
        raise RuntimeError('Das Agent-Kontingent muss überprüft werden.')
    usage = api('/v1/workspace/analytics/query/usage-by-product-over-time', {
        'start_time': period_start(reset) * 1000, 'end_time': int(time.time() * 1000),
        'interval_seconds': 86400, 'group_by': ['product_type']})
    columns = usage['columns']
    minute_index, product_index = columns.index('total_minutes'), columns.index('product_type')
    used = sum(float(row[minute_index] or 0) * 60 for row in usage['rows']
               if str(row[product_index]).upper().replace(' ', '_') in {'CONVAI', 'AGENTS', 'CONVERSATIONAL_AI'})
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {'reset': reset, 'settled': 0, 'reservations': {}}
    if ledger['reset'] != reset:
        ledger = {'reset': reset, 'settled': 0, 'reservations': {}}
    # Provider reporting may lag. Local settled usage is a high-water safeguard.
    used = max(used, ledger['settled']) + sum(r['seconds'] for r in ledger['reservations'].values())
    return ledger, max(0, allowance - BUFFER_SECONDS - used)


def session(data):
    import uuid
    raw = data.get('profiles')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 3:
        raise ValueError('Eine bis drei Personen auswählen.')
    profiles = [clean_profile(p) for p in raw]
    voice = data.get('voice', 'female')
    if voice not in VOICES:
        raise ValueError('Ungültige Stimme.')
    with LOCK:
        try:
            config = json.loads(CONFIG.read_text())
            ledger, remaining = budget()
            if remaining < SESSION_SECONDS:
                return {'backend': 'classic', 'reason': 'allowance', 'remaining_seconds': remaining}
            reservation = uuid.uuid4().hex
            ledger['reservations'][reservation] = {'seconds': SESSION_SECONDS, 'created': time.time()}
            save(LEDGER, ledger)
            try:
                token = api('/v1/convai/conversation/token?agent_id=' + config['agent_id'])['token']
            except Exception:
                # Keep reservation on ambiguous network errors (token may exist).
                raise
            return {'backend': 'agents', 'token': token, 'reservation': reservation,
                    'voice_id': VOICES[voice], 'profiles': json.dumps(profiles, ensure_ascii=False),
                    'group_rules': GROUP_RULES if len(profiles) > 1 else '',
                    'max_seconds': SESSION_SECONDS, 'remaining_seconds': remaining}
        except (RuntimeError, OSError, KeyError, ValueError):
            return {'backend': 'classic', 'reason': 'usage-unavailable'}


def settle(data):
    conversation_id = str(data.get('conversation_id', ''))
    if not conversation_id.startswith('conv_') or not conversation_id.replace('_', '').isalnum():
        raise ValueError('Ungültiges Gespräch.')
    with LOCK:
        config = json.loads(CONFIG.read_text())
        ledger = json.loads(LEDGER.read_text())
        reservation = ledger['reservations'].get(data.get('reservation'))
        if not reservation:
            return {'settled': False}
        details = api('/v1/convai/conversations/' + conversation_id)
        if conversation_id in ledger.get('settled_conversations', []):
            return {'settled': False}
        if details.get('agent_id') != config['agent_id'] or details.get('status') not in {'done', 'failed'}:
            return {'settled': False}
        metadata = details.get('metadata', {})
        if abs(metadata.get('start_time_unix_secs', 0) - reservation['created']) > 180:
            return {'settled': False}
        # Don't accept browser-reported duration; only provider metadata.
        seconds = max(0, float(metadata['call_duration_secs']))
        ledger['settled'] += seconds
        ledger.setdefault('settled_conversations', []).append(conversation_id)
        del ledger['reservations'][data['reservation']]
        save(LEDGER, ledger)
        return {'settled': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    args = parser.parse_args()
    if args.setup:
        setup()
