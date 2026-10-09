"""Private operational email alerts. Never include logs, credentials or user data."""
import argparse
import fcntl
import json
import os
import smtplib
import ssl
import subprocess
import time
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
from urllib.request import urlopen


def failures(checks, run=subprocess.run):
    result = []
    for check in checks:
        unit = check['unit']
        if not unit.replace('-', '').replace('.', '').replace('@', '').isalnum():
            raise ValueError('Invalid unit')
        status = run(['systemctl', 'show', unit, '--property=LoadState,ActiveState,Result'],
                     capture_output=True, text=True, timeout=10, check=True)
        values = dict(line.split('=', 1) for line in status.stdout.splitlines() if '=' in line)
        if values.get('LoadState') != 'loaded':
            result.append(check['label'] + ': nicht geladen')
        elif check['kind'] in ('daemon', 'timer') and values.get('ActiveState') != 'active':
            result.append(check['label'] + ': nicht aktiv')
        elif check['kind'] == 'job' and values.get('Result') != 'success':
            result.append(check['label'] + ': Prüfung fehlgeschlagen')
        elif check['kind'] not in ('job', 'daemon', 'timer'):
            raise ValueError('Invalid check kind')
    return sorted(result)


def notification(previous, issues, now, cooldown=6 * 3600):
    before = previous.get('issues', [])
    if issues and (issues != before or now - previous.get('sent', 0) >= cooldown):
        return 'failure'
    if not issues and before:
        return 'recovery'
    return None


def send(config, subject, body):
    message = EmailMessage()
    message['From'] = config['smtp_user']
    message['To'] = config['recipient']
    message['Subject'] = subject
    message['Date'] = formatdate(localtime=False)
    message.set_content(body)
    with smtplib.SMTP('mail.infomaniak.com', 587, timeout=20) as client:
        client.ehlo()
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
        client.login(config['smtp_user'], config['smtp_password'])
        refused = client.send_message(message)
        if refused:
            raise RuntimeError('Notification rejected')


def public_available(url):
    if url not in ('https://demenzfreundlich-kreis6.ch/zaeme/',
                   'https://auth.myna-ai.ch/.well-known/openid-configuration'):
        raise ValueError('Unexpected probe destination')
    try:
        with urlopen(url, timeout=10, context=ssl.create_default_context()) as response:
            return response.status == 200
    except Exception:
        return False


def poll(config, state, *, now=None, inspect=failures, deliver=send, probe=public_available):
    now = int(time.time()) if now is None else now
    issues = inspect(config['checks'])
    if config.get('probe_url') and not probe(config['probe_url']):
        issues.append('Öffentlicher Zugang: nicht erreichbar')
    issues = sorted(issues)
    action = notification(state, issues, now)
    if action:
        title = 'Betriebsalarm' if action == 'failure' else 'Betrieb wieder normal'
        details = '\n'.join(issues) if issues else 'Alle überwachten Prüfungen sind wieder erfolgreich.'
        deliver(config, '[MYNA] ' + title + ' – ' + config['label'],
                config['label'] + '\n\n' + details +
                '\n\nBitte den Dienststatus im geschützten Administrationszugang prüfen.'
                '\nDiese Meldung enthält keine Nutzer- oder Gesprächsdaten.')
    return {'issues': issues, 'sent': now if action else state.get('sent', 0)}, action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    config_path = Path('/etc/myna-monitor/config.json')
    if config_path.stat().st_mode & 0o077:
        raise RuntimeError('Monitor configuration must be private')
    config = json.loads(config_path.read_text())
    root = Path('/var/lib/myna-monitor')
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    with (root / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.test:
            send(config, '[MYNA] Test Betriebsalarme – ' + config['label'],
                 'Dies ist die angeforderte Testnachricht für die Betriebsalarme von ' + config['label'] +
                 '.\n\nEmpfänger: ' + config['recipient'] +
                 '\nÜberwacht werden Dienststatus, Löschkontrolle und/oder Backupkontrolle.'
                 '\nEs werden keine Nutzer- oder Gesprächsdaten mitgeschickt.'
                 '\n\nDies ist ein Versandtest, keine Störungsmeldung.')
            print('Test notification accepted by SMTP server; inbox delivery not independently verified.')
            return 0
        path = root / 'state.json'
        state = json.loads(path.read_text()) if path.exists() else {}
        updated, action = poll(config, state)
        temporary = root / 'state.tmp'
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as output:
            json.dump(updated, output)
        os.replace(temporary, path)
        print(json.dumps({'issues': len(updated['issues']), 'notification': action or 'none'}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # SMTP failures may include account data: do not log exception text.
        print('Operational monitoring failed; check private configuration and connectivity.')
        raise SystemExit(1)
