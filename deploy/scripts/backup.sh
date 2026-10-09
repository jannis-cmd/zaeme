#!/bin/bash
# Encrypted app recovery material. Never send this archive to an email recipient.
set -euo pipefail
umask 077
runtime=/run/zaeme-backup
output=/var/backups/zaeme/encrypted
recipient_file=/etc/zaeme-backup/recipient.txt
mkdir -p "$runtime" "$output"
exec 9>"$runtime/lock"
flock -n 9 || exit 0
recipient=$(sed -n 's/^Public key: //p' "$recipient_file")
[[ "$recipient" == age1* ]] || { echo 'Backup recipient missing' >&2; exit 1; }
stage=$(mktemp -d "$runtime/stage.XXXXXX")
archive="$output/zaeme-$(date -u +%Y%m%dT%H%M%SZ).tar.gz.age"
trap 'rm -rf "$stage"; rm -f "$archive.tmp"' EXIT
mkdir "$stage/config" "$stage/state"
cp -a /etc/zaeme/. "$stage/config/"
python3 -I - "$stage/state/auth.sqlite3" <<'PY'
import os,sqlite3,sys
with sqlite3.connect('file:/var/lib/zaeme/auth.sqlite3?mode=ro',uri=True) as source:
    with sqlite3.connect(sys.argv[1]) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup integrity check failed')
os.chmod(sys.argv[1],0o600)
PY
cp /var/lib/zaeme/agents-budget.json "$stage/state/"
readlink /opt/zaeme/current > "$stage/release.txt"
cp -a /opt/zaeme/current/deploy "$stage/deploy"
printf '%s\n' 'Encrypted Zäme recovery backup. Browser-local books are not included.' 'Restore offline; invalidate app sessions and grants, reconcile provider deletions and later revocations before resuming processing.' > "$stage/RESTORE.txt"
tar -C "$stage" -czf - . | age -r "$recipient" -o "$archive.tmp"
mv -n "$archive.tmp" "$archive"
[[ -s "$archive" ]] || { echo 'Backup archive missing' >&2; exit 1; }
# Only this job's encrypted archives are subject to its 14-day retention.
find "$output" -maxdepth 1 -type f -name 'zaeme-*.tar.gz.age' -mmin +20160 -delete
printf '%s\n' 'Encrypted Zäme backup completed.'
