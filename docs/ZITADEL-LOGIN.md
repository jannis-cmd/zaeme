# ZITADEL login and guest access

The hosted app uses `https://auth.myna-ai.ch` with authorization code, S256 PKCE,
`client_secret_basic` and `openid profile email`. Infomaniak supplies authentication
emails and the BYO language model; it is not the identity provider.

Authlib validates state, signed ID tokens, issuer, audience, expiry and nonce.
If the ID token omits email, the userinfo endpoint supplies it only after the
subject has been matched. Missing email never restarts login on an account click.
OAuth tokens are discarded after validation. Seven-day app sessions use random
opaque Secure/HttpOnly/SameSite=Lax cookies scoped to `/zaeme/`; only hashes are
stored in SQLite. Every POST needs the exact public Origin. Logout revokes the
app session and directs the browser to ZITADEL's end-session endpoint.

## Access rules

- Guests can create one book and speak for five minutes total per browser,
  once, across reloads and days. Existing books are not truncated; guests can
  select one of them. A server WebSocket relay closes the provider connection
  at the deadline, counts elapsed connected time, and permits resuming the
  remaining time. Setup before the relay opens does not consume speaking time;
  provider connection setup after opening the relay counts toward the allowance.
- Guests receive an expiring, single-use, browser-bound relay ticket, never an
  ElevenLabs conversation credential. The relay binds the validated profile and
  voice. Guests cannot obtain classic-mode tokens or bypass the relay via chat.
- Logged-in accounts have no application quota for person count or accumulated
  conversation time. Provider availability, the shared operator budget, existing
  ten-minute Agent call duration and provider concurrency still apply. A busy
  provider fails clearly; call queueing remains disabled.
- An anonymous browser can reset its identity by deleting cookies or using a
  different browser. This is a trial allowance, not a person-level entitlement.

Books remain in unencrypted localStorage. The first login on an origin moves
existing guest books into an account-specific local namespace; later accounts
have separate local libraries. Logout hides account books from the normal UI.
This prevents accidental account mixing, not access by someone controlling the
browser or another same-origin script. There is no device synchronization.
Changing domain does not transfer browser data: old preview books remain on
the original origin. Keep them there until explicitly migrated or exported.

## Runtime

Install `requirements-web.txt` and build the SDK with `npm ci && npm run build`.
Keep secrets outside the source/web root. `ZAEME_AUTH_CONFIG` points to:

```json
{
  "client_id": "FROM_ZITADEL",
  "client_secret": "FROM_ZITADEL",
  "cookie_secret": "LONG_RANDOM_SECRET",
  "public_url": "https://demenzfreundlich-kreis6.ch/zaeme",
  "database": "/var/lib/zaeme/auth.sqlite3",
  "upstream": "http://127.0.0.1:4185"
}
```

Register only the exact `/zaeme/auth/callback` and post-logout `/zaeme/` URLs.
Optionally add `trusted_proxy_cidrs` to the private configuration as an array of
the actual reverse proxy's IP addresses or tightly scoped CIDRs. With the default
empty array, forwarded headers are ignored. The proxy must overwrite untrusted
client-supplied forwarded headers. Recheck this setting if its container address
changes. SQLite stores request-burst counters across restarts; these do not add an
accumulated-time or person-count quota for accounts. The app permits 240 requests
per minute per client IP, with lower per-route limits for login, voice setup,
summaries and transcription. Expired burst counters are pruned after two windows.

The front service attaches a fresh nonce to the inline session bootstrap and
allows only the local app and required voice domains in its CSP. Blob URLs remain
allowed for SDK audio worklets; inline styles support existing dynamic layout.

The optional persona text agent reuses the existing ElevenLabs BYO LLM secret:
run `agents_service.py --setup-persona`, then set `ZAEME_PERSONA_VIA_AGENT=1`.
Its prompt is the same `PERSONA_RULES` used by the direct model adapter. This
adds ElevenLabs text-agent processing; the Infomaniak secret is never exported.
Its one-minute reservation shares the durable workspace usage guard.
The classic fallback additionally needs its own direct model key. Without that
key it fails clearly if Agent service/budget is unavailable.

`deploy/` contains systemd units and the Caddy fragment for myna-1. The private
Agents gateway binds only to loopback. The front service binds to the existing
Caddy bridge address, with a matching firewall restriction. The prefix must be
preserved, and all other website routes keep their original handler. No new
public application port is opened. Run Gunicorn with threads for WebSockets.
Keep URL/query access logging disabled: OAuth callbacks and relay paths contain
short-lived credentials. SQLite holds session identifiers, guest usage and
short-lived encrypted connection payloads, not a permanent profile database.
Back up `/etc/zaeme` and `/var/lib/zaeme` privately; coordinate reservation state
when moving the runtime to avoid duplicating outstanding provider reservations.

## Verification

Python tests cover signed-token validation, CSRF, logout replay, guest profile
validation, non-disclosure of provider credentials, durable partial/exhausted
allowances, expired/replayed/cross-browser tickets and crash accounting.
JavaScript tests cover production limits, preservation of old books, first-login
migration and separate account libraries. A real provider login and logout is
still required to validate the deployed client end to end. Test with invented
profiles, including a full five-minute trial and pause/resume.

References: [ZITADEL endpoints](https://zitadel.com/docs/apis/openidoauth/endpoints),
[ElevenLabs chat mode](https://elevenlabs.io/docs/eleven-agents/guides/chat-mode),
[Flask-Sock deployment](https://flask-sock.readthedocs.io/en/latest/web_servers.html).
