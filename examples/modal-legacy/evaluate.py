"""Run the legacy Hearth dialogue set against the standalone Modal prototype.

Usage: python3 evaluate.py https://your-modal-url
No results are uploaded or saved; review the printed replies against each criterion.
"""

import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 evaluate.py BACKEND_URL")
    base = sys.argv[1].rstrip("/")
    code = getpass.getpass("Hearth access code: ")
    cases = json.loads(Path(__file__).with_name("eval_cases.json").read_text())
    profile = {
        "name": "Marta",
        "language": "English",
        "topics": "Marta likes roses and used to garden. Her daughter is named Ana.",
        "avoid": "",
    }
    for case in cases:
        payload = json.dumps({"profile": profile, "messages": [{"role": "user", "content": case["user"]}]}).encode()
        request = urllib.request.Request(
            base + "/chat",
            data=payload,
            headers={"Content-Type": "application/json", "X-Hearth-Access": code},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                reply = json.load(response)["response"]
        except urllib.error.HTTPError as error:
            reply = f"HTTP {error.code}: {error.read().decode()[:300]}"
        print(f"\n{case['id']}\nUser: {case['user']}\nHearth: {reply}\nReview: {case['review']}")


if __name__ == "__main__":
    main()
