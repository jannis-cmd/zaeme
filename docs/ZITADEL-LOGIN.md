# ZITADEL login and privacy enforcement

The hosted app uses `https://auth.myna-ai.ch` with authorization code, S256 PKCE,
`client_secret_basic` and `openid profile email`. Infomaniak supplies authentication
emails and the BYO language model; ZITADEL is the identity provider.

Authlib validates state, signed ID tokens, issuer, audience, expiry and nonce.
Userinfo must match the validated subject. OAuth tokens are discarded. Seven-day
app sessions use opaque Secure/HttpOnly/SameSite=Lax cookies scoped to `/zaeme/`;
SQLite stores only token hashes. POST and voice connections require the exact
public Origin. Logout revokes the app session and redirects to ZITADEL logout.
The account menu also offers revocation of all app sessions; this does not sign
out other applications or automatically disable the ZITADEL account.

## Access and storage

Login is mandatory for books, summaries and conversations. The logged-out family
shell displays a login explanation without profile contents. Donations and legal
pages remain public. There is no guest trial and no automatic guest-book import.

Accounts have no person-count or accumulated-time quota. Technical ten-minute
calls, request-burst limits, shared provider budgets and concurrency still apply.
All hosted conversations use an expiring, single-use, session-bound server relay
ticket. The browser never receives an ElevenLabs conversation credential. The
relay binds validated profile/voice settings, checks consent/session revocation
throughout the call and tracks provider conversation IDs. Classic chat, speech,
Scribe and transcription routes are disabled publicly. Missing Agent availability
fails clearly instead of falling back to an uncontrolled processing path.

New books require explicit, versioned consent and separate acceptance of terms
before collection. The server binds receipts to account, book and version and
checks every selected book before provider transfer. Real profiles are disabled
by default; the operator gates and evidence needed to enable individual accounts
are described in [privacy operations](PRIVACY-OPERATIONS.md). AI summaries remain
proposals until a person reviews and accepts them.

Books stay in unencrypted localStorage, separated by account namespace. Logout
hides them in the normal UI. There is no device synchronization or protection
against another same-origin script or someone controlling the browser. The
shared customer website origin remains a risk boundary, not an isolated app.
Revocation blocks processing; deletion removes the current local book after
server confirmation and queues associated provider conversations for deletion.
Offline requests remain visibly pending. Exports and other devices need separate
handling. The deletion worker retries failures and discovers missing provider
IDs using random per-request correlation IDs rather than real account IDs.

## Runtime

Install `requirements-web.txt` and build with `npm ci && npm run build`.
Keep all secrets outside source and web roots. Set `ZAEME_AUTH_CONFIG` to the same
private JSON file for the front service, gateways and privacy worker:

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

Missing privacy configuration leaves real profiles disabled. Do not copy approval
flags into an example as if contracts or a risk review had been completed.
Register only the exact `/zaeme/auth/callback` and post-logout `/zaeme/` URLs.
Optional `trusted_proxy_cidrs` must match actual proxies; forwarded headers are
otherwise ignored. The proxy must overwrite client-supplied forwarded headers.

The persona text agent uses the existing ElevenLabs BYO LLM secret: configure
with `agents_service.py --setup-persona`, then set `ZAEME_PERSONA_VIA_AGENT=1`.
Hosted summaries fail closed without this controlled agent path. The underlying
Infomaniak secret is never exported to the browser.

Install the units from `deploy/`. Both gateways remain private on loopback;
Gunicorn needs threads for WebSockets. Preserve the `/zaeme/` prefix in Caddy and
leave other customer website routes unchanged. The privacy timer runs every five
minutes; install and enable `zaeme-privacy.timer`. Its user needs the auth database
and provider key. Check `privacy_admin.py --status` and worker failures regularly;
the timer alone does not provide off-server alerting.

The CSP allows same-origin connections and SDK blob worklets. Keep URL/query
access logging disabled: callbacks and relay paths contain credentials. Never log
profile content or provider responses. Back up `/etc/zaeme` and `/var/lib/zaeme`
privately; after restoration reapply revocations and pending deletions before
allowing processing. See the detailed operator runbook.

## Verification

Run `npm test`, the Python unittest suite and `npm run build`. Tests cover OIDC,
CSRF, login-only processing, account isolation, explicit consent, wrong-owner and
stale receipts, grouped revocation, session expiry, provider ID discovery and
retryable deletion. UI tests cover the login gate, consent before collection,
summary review and offline revocation. Test desktop/mobile layout and a real
synthetic-profile login/voice/logout separately; mocked tests do not establish
provider compliance or clinical safety.
