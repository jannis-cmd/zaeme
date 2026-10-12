# Privacy operations

This is a technical self-hosting checklist, not legal advice or a record of a live deployment. Use fictional profiles until provider agreements, consent, representation, data transfers and risks have been reviewed for your intended use. Keep operator identities, contracts, account subjects and evidence outside the repository.

## Deployment prerequisites

Replace `impressum.html`, `datenschutz.html` and `nutzungsbedingungen.html` with accurate, reviewed operator documents. Provide a working privacy contact and describe actual providers, locations, retention, backups and rights handling. The hosted service refuses startup without `legal_documents_ready: true`; that flag acknowledges your review, not compliance.

Keep invitation access enabled and require verified sign-in. Do not bypass the controlled Agents relay with the private classic adapter. Hosted voice notes and separate transcription routes remain disabled.

Real profiles require all three explicit private settings:

- `privacy.real_profiles_enabled: true`
- `privacy.provider_contracts_confirmed: true`
- `privacy.risk_review_approved: true`

Restricted access is the default and additionally requires the account subject in `privacy.approved_subjects`. `privacy.real_profiles_access: "public"` removes that allowlist for authenticated users only; unknown modes deny access. Never copy approval flags into a public example or treat them as evidence of informed consent or authority.

Review applicable provider terms and restrictions, account permissions, processing roles, subprocessors, countries and transfer safeguards. Check retention, training-use settings and deletion with fictional test data. Do not claim zero retention, residency or contractual approval based only on the code. Clinical usefulness has not been established.

## Consent and local storage

Each book requires current versioned consent and separate terms acceptance before collection. Each call requires fresh notice for all selected participants. Being a family member does not by itself establish authority to consent. Respect refusal, discomfort and requests to stop.

Books remain unencrypted in account-namespaced localStorage. Another script on the same origin or someone controlling the browser may read them. Prefer a dedicated origin. There is no cross-device synchronization.

A confirmed revocation blocks new processing and ends associated active relays. Offline requests initially block only the local client and remain pending until the server confirms. Do not claim that provider deletion is complete merely because revocation succeeded.

## Requests, deletion and exports

Use the configured operator contact to authenticate requests with the minimum necessary evidence. Do not request identity or health documents in public issues or book text.

- `privacy_admin.py --status`: inspect pending deletion and unresolved correlation requests.
- `privacy_admin.py --drain`: retry provider discovery/deletion and scheduled cleanup.
- `privacy_admin.py --check`: detect stale cleanup and overdue unresolved work.
- `privacy_admin.py --revoke-user OIDC_SUBJECT`: revoke the account's app sessions and books.
- `privacy_admin.py --export-user OIDC_SUBJECT --output PRIVATE_NEW_PATH`: export technical privacy records; add `--include-conversations` for provider conversation data.

Run commands only in the protected service environment with `ZAEME_AUTH_CONFIG` and provider credentials. Confirm export completeness before delivery; securely transmit and remove exports when no longer needed. Commands do not automatically export browser-local books.

The worker retries failed provider deletions and uses random request correlations to discover missing provider IDs. A group-book revocation queues the entire linked group conversation, including other participants' contributions. Investigate failures rather than marking them complete.

App-wide logout does not delete identity-provider accounts, local books or accounts in other services. Clearing browser storage does not notify the server; revoke first while the association remains available.

## Retention and recovery

The implementation includes a 90-day cleanup window for eligible revoked receipts/events and deleted resource records. Outstanding deletion work is retained. The worker queues day-old active provider resources for deletion. These are code defaults, not a legal retention assessment; reconcile them with your actual contracts and notices.

Install the privacy timer and check timer; inspect failures and configure off-server alerting. Example monitoring runs every five minutes and throttles unchanged alerts. A timer alone does not prove successful cleanup or end-to-end delivery.

Example encrypted backups use SQLite's backup API and an external public age recipient. Keep the recovery key separate. Defaults retain this job's encrypted archives for 14 days. Operator-owned programs executed by root must not be writable by the app user. Backups need independent replication, retention review and restore drills.

Before restoring:

1. Block public access and outbound provider processing.
2. Reapply subsequent access revocations, consent withdrawals and pending deletions.
3. Invalidate restored sessions; do not revive revoked grants.
4. Reconcile provider records and outstanding deletion jobs.
5. Resume only after a documented verification.

## Incidents and changes

Pause affected processing, revoke sessions/relays, protect necessary evidence and contact relevant providers. Assess notification duties with qualified advice. Do not publish credentials, transcripts or exploitable incident details.

For material changes, update notices and consent versions together and request fresh consent; old receipts are not consent to a new purpose. Keep private operational evidence rather than deployment incident diaries in this public repository.
