# Project status

Zäme is an **experimental, fictional-profile prototype**. It is not approved for care or medical use. There is no promised public-release date or clinical benefit claim.

This repository is deployment-neutral. It contains no live-service URL, operator identity, account configuration or hosting affiliation. Examples describe available controls, not proof that any particular deployment has configured them correctly.

## Implemented boundaries

- Authenticated self-hosting uses verified ZITADEL login and invitation-only access by default.
- Every selected book needs versioned consent and separate terms acceptance. Each conversation needs fresh participant notice.
- Real-person profiles are disabled by default. Operator approval flags are not legal or clinical approval.
- AI summaries remain proposals until reviewed. Conversations do not write facts into books.
- Browser books are local and unencrypted. Account namespaces do not isolate them from another script on the same origin.
- The main voice path is a controlled ElevenLabs Agents relay. The model can use compatible APIs, including Infomaniak or Modal. Provider processing is not necessarily Swiss- or EU-only.
- Public classic speech/transcription routes are disabled. Development adapters are not authenticated hosting alternatives.
- Deletion retries, cost reservations, rate limits and example backup/monitoring services are included. Operators must install, configure and verify them.

## Before real-person use

Document provider permissions, processing roles, retention, deletion, international transfers, valid consent or representation, and a risk assessment. Verify accessibility with intended users and care partners. Evaluate alternative voice/agent providers against the same requirements.

The legal HTML files are **templates**, not a deployed operator's legal documents. Replace them, provide a real contact channel, review consent versions, and explicitly set `legal_documents_ready: true` only after review. Keep supporting contracts and evidence outside Git.

See [security](../SECURITY.md), [self-hosting](ZITADEL-LOGIN.md) and [privacy operations](PRIVACY-OPERATIONS.md). Public source code is not permission to process sensitive data or use someone else's provider account.
