# Security review — 8 October 2026

This review covered the hosted app, browser code, authentication/session flow,
guest voice relay, provider adapters, deployment configuration, repository history
and the shared authentication host. It is a maintenance review, not an independent
penetration test or a guarantee of security.

## Changes

- Added durable, secret-keyed per-IP request-burst controls, with explicitly
  configured trusted proxies. Forwarded headers from other peers are ignored.
- Added per-response CSP nonces, framing and browser-permission restrictions,
  request-body bounds and API method checks. Guest records are no longer allocated
  for static assets; expired transient relay payloads are removed.
- Validated voice upstream URLs, malformed voice/reservation inputs and WebSocket
  messages. Reduced model retries to fit the web request deadline.
- Removed the unused `examples/modal-legacy` prototype and stale documentation,
  consolidated duplicate preview budget handling and removed response rewriting.
  Supported model adapters and classic fallback remain available.
- Added pinned Python runtime dependencies and CI for JavaScript/Python tests,
  builds and dependency audits. Enabled repository dependency security updates;
  secret scanning and push protection were already enabled.
- Hardened authentication-host file permissions, container privileges and writable
  mounts, restricted unused public endpoints, and applied host security updates.
  Verified an encrypted backup by restoring its database into an isolated instance.

## Verification

- 42 JavaScript and 66 Python tests passed. These include real signed OIDC token
  rejection cases, CSRF/session replay, hostile bootstrap text, request bursts,
  proxy spoofing and guest WebSocket deadline/replay/origin checks.
- The production frontend built successfully. npm and the pinned Python runtime
  audit reported no known dependency vulnerabilities at review time.
- Working-tree and complete Git-history secret scans found no leaks. A separate
  exact-match check against locally configured credentials also found no matches.
  These checks cannot establish the absence of every kind of sensitive data.
- HTTPS pages and login discovery remained available; internal app, SSH and
  database ports were not publicly reachable in external TCP checks. The live app
  opened without CSP errors in the tested browser flow.

## Remaining work

Official authentication-service images still have dependency findings. Unused
surfaces were restricted and reachability was assessed, but upstream patching
and repeat scanning remain necessary. Detailed host findings and recovery
material are kept outside this public repository.

Provider abuse policies need administrator verification. A complete live
sign-in/out and voice call should be repeated after provider changes. Automated
off-server backup
delivery, restore drills and actionable monitoring need an operational owner.

See [SECURITY.md](../SECURITY.md) for important product boundaries: browser-local
unencrypted books, shared-origin trust, anonymous cookie reset, seven-day app
sessions and external model/voice processing.
