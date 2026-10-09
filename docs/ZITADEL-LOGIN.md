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

Install the `zaeme-*` units from `deploy/` on the app host; `myna-auth-*` checks
belong only on the authentication host. Both gateways remain private on loopback;
Gunicorn needs threads for WebSockets. Preserve the `/zaeme/` prefix in Caddy and
leave other customer website routes unchanged. The privacy timer runs every five
minutes; install and enable `zaeme-privacy.timer`. Its user needs the auth database
and provider key. Check `privacy_admin.py --status` and worker failures regularly;
the timer alone does not provide off-server alerting.

The CSP allows same-origin connections and SDK blob worklets. Keep URL/query
access logging disabled: callbacks and relay paths contain credentials. Never log
profile content or provider responses. Back up `/etc/zaeme` and `/var/lib/zaeme`
privately. The daily encrypted backup uses a root-owned copy of
`deploy/scripts/backup.sh` at `/usr/local/sbin/zaeme-backup`, not executable
code owned by the app user. Install `age` from the official OS repository and
configure only the public recipient under `/etc/zaeme-backup/recipient.txt`.
The hourly backup check uses a root-owned copy of `backup_check.py` and isolated
Python. Off-server replication still requires operational configuration.
The root-owned `myna-monitor` service provides Infomaniak SMTP alerts on both
hosts; keep its recipient/credentials outside the repository. After restoration reapply revocations and pending deletions before
allowing processing. See the detailed operator runbook.

## Verification

Run `npm test`, the Python unittest suite and `npm run build`. Tests cover OIDC,
CSRF, login-only processing, account isolation, explicit consent, wrong-owner and
stale receipts, grouped revocation, session expiry, provider ID discovery and
retryable deletion. UI tests cover the login gate, consent before collection,
summary review and offline revocation. Test desktop/mobile layout and a real
synthetic-profile login/voice/logout separately; mocked tests do not establish
provider compliance or clinical safety.

## Conversation notice and public access policy

Hosted `/api/agents/session` requests require `voice_notice` with the runtime
`privacy.voice_notice_version` as `version` and boolean `confirmed: true`.
The UI requests this afresh before each microphone/provider start. Cancellation
or changes to selected books invalidate it. Notice records are owner-bound.

Real profiles require all three explicit privacy approval flags. After a
documented public-launch decision, `privacy.real_profiles_access: "public"`
allows every authenticated account without an allowlist. Missing mode defaults
to `restricted` and requires `approved_subjects`; unknown modes deny access.
The release does not itself supply or approve these operational decisions.

Install `zaeme-privacy-check.timer` alongside the cleanup timer. `--check` fails
for stale cleanup (>15 minutes) or pending resources/unresolved requests older
than 24 hours. Systemd status is local monitoring; the additional `myna-monitor.timer` sends operational alerts. Independent
whole-host outage detection remains separate.

## Invitation-only Zäme access

Hosted access defaults to `invite_only: true`. ZITADEL remains the shared identity
provider; registration of a shared account does not grant Zäme access. Existing
app sessions are not grandfathered. Set `invitation_admin_subjects` in the private
config to the operator's exact validated ZITADEL subject identifiers. Never grant
operator access by email string or expose this configuration through the browser.

Operators open `/zaeme/access` or use **Einladungen verwalten** in the account
menu. Each link is shown once, uses 256 bits of randomness, is single-use and
expires after 7 days by default (1 or 30 days selectable). Send it privately to
one recipient. Possession of the link authorises its first verified redeemer;
it is not bound to a preselected email address. Raw tokens are not stored in
SQLite, not sent to ZITADEL and not included in access logs.

GET requests only establish pending browser state and redirect to a clean URL;
mail link scanners do not consume invitations. OIDC still validates state, nonce,
signature, issuer, audience and PKCE. Redemption requires verified email and an
atomic database transaction; only one concurrent redeemer succeeds. Zäme grants
are bound to subject IDs, not email addresses. Link expiry does not terminate
an issued access grant. Revocation blocks existing sessions and running voice
relays; privacy export/revocation remain available to signed-in accounts.

Invitation management requires the operator subject and a session-bound CSRF token on native forms. Foreign Origins are rejected; missing or null Origins require the same token. API POSTs still require the exact public Origin.
Non-invited accounts cannot call profile, consent-grant or voice endpoints, and
receive the invitation gate rather than the app. Legal documents remain public.
The existing privacy approval gates for real profiles are independent and unchanged.

The privacy cleanup timer removes expired unused invitations after 30 days and
revoked invitations/access records after 30 days. Include these tables in the
existing encrypted SQLite backups. Restore must reapply later invitation
revocations before access resumes; do not revive revoked grants from an old backup.

For a temporary full pause, stop/disable both web and gateway units and use the
edge pause handler. To run the restricted app, enable both units and restore the
edge proxy only after verifying `invite_only: true`, operator subjects and access
tests. Public registration at the shared identity provider is intentionally not
disabled for other applications.
