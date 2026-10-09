"""Private operator commands for Zäme rights requests and deletion retries.

Use the same owner-readable ZAEME_AUTH_CONFIG and provider-key environment as
runtime. Never expose this module through the web gateway. No profile contents,
account identifiers or provider credentials are printed.
"""
import argparse
import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from privacy_store import PrivacyStore


def delete_conversation(resource):
    key_path = os.environ.get('ELEVENLABS_AGENTS_KEY_FILE')
    if not key_path:
        raise RuntimeError('Provider key is not configured')
    key = Path(key_path).read_text().strip()
    request = Request('https://api.elevenlabs.io/v1/convai/conversations/' + resource,
                      headers={'xi-api-key': key}, method='DELETE')
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in {200, 202, 204}:
                raise RuntimeError('Unexpected provider response')
            # 202 means asynchronous acceptance, not confirmed deletion.
            if response.status == 202:
                raise RuntimeError('Provider deletion is not yet confirmed')
    except HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError('Provider deletion failed (HTTP ' + str(exc.code) + ')') from None


def discover_conversations(correlation):
    from agents_service import api
    from urllib.parse import urlencode
    cursor = None
    records = []
    for _ in range(10):
        query = {'user_id': correlation, 'page_size': 100}
        if cursor:
            query['cursor'] = cursor
        result = api('/v1/convai/conversations?' + urlencode(query))
        records.extend(row['conversation_id'] for row in result.get('conversations', []))
        if not result.get('has_more'):
            return records
        cursor = result['next_cursor']
    raise RuntimeError('Discovery incomplete')


def reconcile_requests(store, discover=discover_conversations):
    with store.db() as connection:
        rows = connection.execute("SELECT * FROM privacy_requests WHERE status='open' ORDER BY last_checked,created LIMIT 50").fetchall()
    failed = 0
    for row in rows:
        # Rotate even empty/failed discoveries so abandoned setups cannot starve
        # later requests whose provider metadata needs recovery.
        with store.db() as connection:
            connection.execute('UPDATE privacy_requests SET last_checked=? WHERE request=?',
                               (time.time_ns(), row['request']))
        try:
            resources = discover(row['request'])
            for resource in resources:
                store.register(row['owner'], json.loads(row['books']), resource, row['request'])
            # Empty lists can reflect provider reporting lag. Keep unresolved
            # requests visible; never silently claim that they contained no data.
        except Exception:
            failed += 1
    return failed


def drain(store, delete=delete_conversation, discover=discover_conversations):
    discovery_failed = reconcile_requests(store, discover)
    store.cleanup()
    now = int(time.time())
    with store.db() as connection:
        rows = connection.execute("SELECT resource,attempts FROM privacy_resources WHERE status='pending' "
                                  'AND next_attempt<=? ORDER BY created LIMIT 50', (now,)).fetchall()
    completed, failed = 0, 0
    for row in rows:
        try:
            delete(row['resource'])
        except Exception:
            # Do not persist exception strings: remote responses may contain data.
            failed += 1
            with store.db() as connection:
                connection.execute('UPDATE privacy_resources SET attempts=attempts+1,next_attempt=? WHERE resource=?',
                                   (now + min(3600, 60 * 2 ** min(row['attempts'], 6)), row['resource']))
        else:
            completed += 1
            with store.db() as connection:
                connection.execute("UPDATE privacy_resources SET status='deleted',next_attempt=0 WHERE resource=?", (row['resource'],))
    with store.db() as connection:
        outstanding = connection.execute("SELECT COUNT(*) FROM privacy_resources WHERE status='pending'").fetchone()[0]
    with store.db() as connection:
        unresolved = connection.execute("SELECT COUNT(*) FROM privacy_requests WHERE status='open'").fetchone()[0]
    return {'completed': completed, 'failed': failed + discovery_failed, 'pending': outstanding, 'unresolved_requests': unresolved}


def revoke_user(store, subject):
    owner = store.owner(subject)
    with store.db() as connection:
        books = [row[0] for row in connection.execute('SELECT book FROM privacy_grants WHERE owner=?', (owner,))]
    for book in books:
        store.revoke(owner, book, delete=True)
    with store.db() as connection:
        connection.execute('DELETE FROM sessions WHERE subject=?', (subject,))
    return {'books_blocked': len(books), 'zaeme_sessions_revoked': True}


def private_json(path, value):
    # Do not overwrite an existing evidence/export file or follow symlinks.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--drain', action='store_true')
    group.add_argument('--status', action='store_true')
    group.add_argument('--revoke-user', metavar='OIDC_SUBJECT')
    group.add_argument('--export-user', metavar='OIDC_SUBJECT')
    parser.add_argument('--output', help='New private output file for an export')
    parser.add_argument('--include-conversations', action='store_true', help='Fetch provider conversation records into the private export')
    args = parser.parse_args()
    config = json.loads(Path(os.environ['ZAEME_AUTH_CONFIG']).read_text())
    store = PrivacyStore(config['database'], config['cookie_secret'])
    if args.drain:
        result = drain(store)
        print(json.dumps(result))
        return 1 if result['failed'] else 0
    if args.revoke_user:
        print(json.dumps(revoke_user(store, args.revoke_user)))
        return 0
    if args.export_user:
        if not args.output:
            parser.error('--export-user requires --output')
        result = store.export(store.owner(args.export_user))
        if args.include_conversations:
            from agents_service import api
            # A failure aborts rather than silently claiming a complete export.
            result['conversations'] = [api('/v1/convai/conversations/' + row['resource'])
                                       for row in result['provider_records'] if row['status'] != 'deleted']
        private_json(args.output, result)
        print('Private export written; browser-local books must be obtained separately.')
        return 0
    with store.db() as connection:
        counts = {row[0]: row[1] for row in connection.execute('SELECT status,COUNT(*) FROM privacy_resources GROUP BY status')}
        counts['unresolved_requests'] = connection.execute("SELECT COUNT(*) FROM privacy_requests WHERE status='open'").fetchone()[0]
    print(json.dumps(counts))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
