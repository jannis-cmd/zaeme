# Security scope

Zäme is currently a private preview, not a production care service. A public source repository is not permission to expose the configured API publicly.

- Keep long-lived provider credentials outside the repository and web root. Use owner-readable secret files and restricted provider keys/spending caps. `.gitignore` is only a safety net: it does not remove secrets already tracked or present in Git history.
- The gateway serves only frontend files and selected assets, not Python source, dotfiles or directory listings. It still has no user authentication, persistent per-user limits or production abuse protection. Its shared daily counters reset on restart.
- Do not publish the gateway directly. Public operation needs access controls, durable quotas/cost controls, request timeouts, trusted-origin checks and a production deployment review. Browser limits are not security boundaries.
- Profiles are stored unencrypted in browser localStorage. Conversation context is held in tab memory. Model requests transmit selected profile fields and summaries; ElevenLabs receives audio and spoken reply text. Neither pipeline is currently approved here for identifiable care data.
- ElevenLabs EU residency is planned, not configured. Use invented test data until data handling, consent and retention are resolved. Demo donation amounts must not be represented as accounting records.

Before committing, inspect staged paths and contents for credentials, recordings, profile exports and private operational files. If a credential is exposed, revoke/rotate it; deleting a file alone does not repair the exposure.

Do not put credentials or personal care data in public issues. Until a private security-reporting channel is established, coordinate directly with the maintainer before sharing a sensitive report.
