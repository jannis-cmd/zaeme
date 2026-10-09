# Security scope

Zäme is an experimental companion, not an approved care or medical service. Use
fictional data until consent, provider processing and retention have been reviewed.
Hosting the login locally does not make the audio or model pipeline Swiss-only.

## Hosted entry point

- Publish `web_service.py` behind HTTPS. Keep `agents_gateway.py` and `gateway.py`
  private on loopback; neither is an authentication service. Static development
  servers must also stay private.
- ZITADEL sign-in uses authorization code, S256 PKCE and a confidential client.
  Authlib validates state, signature, issuer, audience, expiry and nonce. Additional
  userinfo must match the validated subject. OAuth tokens are discarded after login.
- App sessions are revocable random opaque cookies, Secure/HttpOnly/SameSite=Lax,
  scoped to `/zaeme/`. Only session-token hashes are stored. Sessions expire after
  seven days. App logout revokes the local session and redirects to ZITADEL logout.
  Disabling a provider account does not immediately revoke existing app sessions;
  incident response must also revoke its app sessions.
- Every POST needs the exact public Origin; the voice relay checks Origin too.
  Host validation, body bounds, CSP nonces, framing protection and restricted
  browser permissions provide additional layers.
- SQLite burst controls survive restart and cookie deletion. Client IPs are keyed
  with HMAC, not stored in plaintext. Trust forwarded IPs only from configured
  reverse-proxy addresses. These limits protect request bursts, not accumulated
  conversation time. They are not volumetric DDoS protection.

## Guest voice and costs

Guests can select one person and try five connected minutes total per browser.
A server WebSocket relay enforces the deadline and uses single-use, expiring,
browser-bound tickets. Guests never receive ElevenLabs conversation credentials
and cannot obtain classic chat, TTS or realtime-Scribe credentials. Pending relay
payloads are encrypted; expired unused payloads and finished calls are purged on
the next dynamic request. Clearing cookies or changing browser can reset an
anonymous identity; this is not a person-level entitlement.

Signed-in accounts have no person-count or accumulated-time quota. They receive
short-lived provider conversation credentials. Operator/provider budgets,
concurrency and technical call duration still apply. Workspace usage and durable
reservations are conservative cost guards, not guaranteed billing caps. The
classic fallback has separate costs and restartable in-memory daily counters.
Configure provider spending limits; do not treat browser controls as boundaries.

## Profiles, credentials and operations

- Books remain unencrypted in browser localStorage. Account namespaces prevent
  accidental mixing in the normal UI; they do not protect against someone
  controlling the browser or another script on the same origin. Hosting under a
  shared website path shares this trust boundary. There is no device synchronization.
- Selected profile facts, summaries, memories, audio and transcripts are processed
  by the configured model/voice services. Audio recording is disabled in Agent
  setup. As verified on 9 October 2026, both live agents request one-day retention
  with transcript/PII and audio deletion for future conversations; this does not
  retroactively delete older data or guarantee zero retention or residency.
  Model-training exclusion at ElevenLabs remains unverified. Never log care text, provider bodies, OAuth callback
  queries or voice-ticket URLs.
- Keep long-lived credentials, SQLite databases, ledgers and recovery material
  outside the repository and web root. Use owner-only files and directories,
  restricted provider keys, least-privilege services, firewall restrictions and
  encrypted backups with an independently stored recovery key.
- Patch the host and pinned dependencies, keep ZITADEL MFA and abuse policies
  configured, and verify encrypted backups can be restored. Automated off-server
  backup delivery and alerting need their own operational setup.

See [deployment](docs/ZITADEL-LOGIN.md) and the
[8 October 2026 review](docs/SECURITY-REVIEW.md) for checks and remaining limitations.

## Before publishing

Inspect staged paths and contents for credentials, recordings, profile exports,
private operational files and sensitive screenshots. Scan the working tree and
Git history; `.gitignore` does not remove already tracked secrets. If a credential
is exposed, revoke/rotate it; deleting the file alone does not repair exposure.
GitHub secret scanning/push protection and dependency alerts supplement this review.

Do not put credentials or personal care data in public issues. Until a private
security-reporting channel is established, coordinate directly with the maintainer
before sharing a sensitive report.
