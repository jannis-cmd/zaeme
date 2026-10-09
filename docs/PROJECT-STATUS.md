# Project status — 9 October 2026

Zäme is staying at an **invitation-only, fictional-profile test stage** for now.
There is no committed public-launch date, care-use approval or development schedule.
MYNA operates the app; the Evangelisch-reformierte Kirchgemeinde Zürich is
responsible for the separate Demenzfreundlich Kreis 6 main website.

## Verified current boundary

- Infomaniak hosts the app and self-hosted ZITADEL identity service in Switzerland.
- New Zäme access needs an operator invitation and verified login. A shared MYNA
  account is insufficient. Invitations are single-use, expiring and revocable.
- Real-person profile approval flags are unset on the live server. Invitations do
  not override that restriction. Content declared fictional cannot be reliably
  checked for real-world identifiability; instructions and human supervision matter.
- Explicit versioned book consent, separate terms acceptance and fresh conversation
  notice are enforced. Audio processing still involves real personal data.
- The hosted app uses ElevenLabs Agents and an Infomaniak BYO model. The complete
  voice pipeline is not confined to Switzerland. No zero-retention claim is made.
- Browser books remain local and unencrypted. Sharing the main website's origin
  is a known trust boundary. There is no cross-device synchronization.
- Provider deletion retries, encrypted daily backups, freshness checks and email
  alerts are enabled. Independent whole-host outage monitoring and automated
  off-server backup replication remain open. A local backup is not disaster recovery.

## Required before expanding use

1. Document actual provider contracts, processing roles, subprocessors, countries,
   transfer safeguards and account-specific settings. Resolve the ElevenAgents
   sensitive-data restriction, applicable end-user agreement and consent-evidence
   retention requirements; edited legal text alone does not establish compliance.
2. Evaluate alternatives to ElevenLabs for speech and orchestration: contractual
   suitability, Swiss/EU processing options, retention and deletion, security,
   accessibility, Swiss German quality and total operating cost. No alternative
   has been selected or deployed. Do not re-enable the private classic route as
   a workaround for missing provider approval.
3. Complete a documented risk assessment and, where required, a DPIA; assess valid
   consent, capacity, representation and the risks for vulnerable participants.
   Address same-origin storage and actual operational recovery capability.
4. Review and update notices, terms, consent versions and real-profile gates
   together before a deliberate launch decision. Keep evidence outside Git.

The [ElevenAgents terms](https://elevenlabs.io/agents-terms) and
[DPA](https://elevenlabs.io/dpa) were consulted on 9 October 2026. Their published
existence does not prove the relevant MYNA account has every required permission.
See the [privacy runbook](PRIVACY-OPERATIONS.md) for the fuller checklist.

## Minimum responsibility while the test stays reachable

Keep OS, containers and dependencies patched; act on security advisories, failed
backups and deletion alerts. Handle access revocations and privacy requests.
Review spending and provider settings. A frozen feature set is not unattended
operation. If this minimum cannot be maintained, pause new access and processing
using the [deployment runbook](ZITADEL-LOGIN.md#invitation-only-zäme-access), while
keeping legal information, contact and rights handling available.

## Public repository boundary

Credentials, account subjects, invitation tokens, databases, recordings, profile
exports, private contracts and recovery keys belong outside this repository.
The current source and reachable Git history were scanned with Gitleaks without
findings on this date; scanners cannot prove the absence of every sensitive value.
Dependency audit results are point-in-time checks, not a security certification.
The source is MIT-licensed; hosted services and partner marks have separate terms.
Report vulnerabilities privately to **info@myna-ai.ch**, without putting sensitive
material into a public issue. Do not send a live secret in the first email.
