# Repository security review

This is an internal maintenance checklist, not a penetration test, clinical approval or security certification. Live infrastructure findings and recovery material do not belong in this public repository.

## Controls to preserve

- Verified OIDC issuer, signed token, state, nonce, audience, expiry and PKCE checks.
- Invitation-only access, session-bound CSRF, exact-Origin API/relay checks.
- Revocable opaque sessions and single-use server-side voice tickets.
- Per-book versioned consent and fresh conversation notice.
- Provider deletion retries, correlation discovery and honest pending status.
- Conservative shared budget accounting, including stale reservation reconciliation.
- Private loopback gateways, restricted file serving and CSP nonces.
- Private secrets/state, least-privilege services, encrypted backups and monitored cleanup.

## Release checks

Run JavaScript and Python tests, build the SDK, audit dependencies and scan the current source and Git history for secrets. Check screenshots and metadata manually; scanners cannot establish the absence of private information.

Exercise synthetic login, consent, voice, revocation and deletion on your own deployment. Test negative cases as well as the happy path. Do not confuse a mocked provider test with an end-to-end deployment check.

## Known limitations

Books remain unencrypted and same-origin accessible in the browser. Group speaker identification is unreliable. Provider contracts, transfers, consent authority, sensitive-data permissions, accessibility and care suitability need separate review. Budget guards are not guaranteed billing caps.

Backup replication, restore capability, independent outage monitoring, patches and privacy requests require an operational owner. See [SECURITY.md](../SECURITY.md) and [privacy operations](PRIVACY-OPERATIONS.md).
