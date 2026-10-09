"""Local freshness check for encrypted archives; does not prove decryption or remote replication."""
import argparse
import json
import stat
import time
from pathlib import Path


def check_directory(directory, pattern, *, now=None, max_age=36 * 3600):
    now = time.time() if now is None else now
    newest = None
    invalid = 0
    for path in Path(directory).glob(pattern):
        try:
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                invalid += 1
                continue
            with path.open('rb') as source:
                if source.readline(64) != b'age-encryption.org/v1\n':
                    invalid += 1
                    continue
            modified = path.stat().st_mtime
            if modified > now + 300:
                invalid += 1
                continue
            newest = max(newest or modified, modified)
        except OSError:
            invalid += 1
    age = max(0, int(now - newest)) if newest is not None else None
    return {'healthy': age is not None and age <= max_age and invalid == 0,
            'latest_archive_age_seconds': age, 'invalid_archives': invalid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--pattern', required=True)
    args = parser.parse_args()
    result = check_directory(args.directory, args.pattern)
    print(json.dumps(result))
    return 0 if result['healthy'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
