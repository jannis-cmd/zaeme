"""Manual live model checks using fictional profiles only.

Run with the same ZAEME_MODEL_* environment as the preview. This makes model API
calls; it does not start a microphone or send saved browser profiles. Inspect
responses for attribution, initiative and silence, not just keyword matches.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from model_client import chat

PROFILES = [
    {'name': 'Marta', 'address': 'du', 'guidance': 'Mag Gartenarbeit.',
     'compiled': 'Ich pflanze gerne Tulpen.', 'notes': ['Mein Sohn heisst Leo.']},
    {'name': 'Otto', 'address': 'Sie', 'guidance': 'Mag Eisenbahnen.',
     'compiled': 'Ich besuche gerne das Verkehrshaus.', 'notes': ['Ich fahre gern mit dem Zug.']},
]
HISTORY = [
    {'role': 'user', 'content': 'Hallo.'},
    {'role': 'assistant', 'content': 'Schön seid ihr beide da.'},
    {'role': 'user', 'content': 'Heute regnet es.'},
    {'role': 'assistant', 'content': 'Dann machen wir es uns drinnen gemütlich.'},
    {'role': 'user', 'content': 'Ja, hier ist es warm.'},
    {'role': 'assistant', 'content': 'Das klingt angenehm.'},
]
CASES = [
    ('initiative', [], 'Uns ist langweilig. Schlag uns ein Thema vor.'),
    ('later-preferences', HISTORY, 'Frage uns nach unseren Präferenzen.'),
    ('later-profile-recall', HISTORY, 'Was mag Otto gerne?'),
    ('direct-address', HISTORY, 'Hallo Otto?'),
    ('facilitation', HISTORY, 'Wie geht es Otto?'),
    ('separate-memory', HISTORY, 'Heisst Ottos Sohn Leo?'),
    ('short-answer', [*HISTORY, {'role': 'assistant', 'content': 'Marta, welche Farbe magst du bei Tulpen?'}], 'Ich weiss nicht.'),
    ('new-topic-after-silence', [*HISTORY, {'role': 'assistant', 'content': 'Marta, welche Farbe magst du bei Tulpen?'}], '...'),
    ('silence-after-one-new-topic', [*HISTORY, {'role': 'assistant', 'content': 'Marta, welche Farbe magst du bei Tulpen?'}, {'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': 'Otto, Sie fahren gerne mit dem Zug. Lieber am See entlang oder durch die Berge?'}], '...'),
    ('requested-quiet', HISTORY, 'Ich möchte jetzt Ruhe. Bitte bleib still, bis ich wieder etwas sage.'),
]


def evaluate(case):
    label, history, text = case
    try:
        result = chat({'profiles': PROFILES, 'messages': [*history, {'role': 'user', 'content': text}]})
        return {'case': label, **result}
    except Exception as error:
        return {'case': label, 'error': type(error).__name__}


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(evaluate, CASES):
            print(json.dumps(result, ensure_ascii=False))
