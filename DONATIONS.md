# Spenden page

The donation surface lives in `index.html`, `donation.css` and `donation.js`. It does not modify the conversation backend. The linked partner marks are original assets from Demenzfreundlich Kreis 6 and MYNA; their branding is not covered by the source code's MIT licence.

`donation.json` holds public configuration only:

- `payment_url`: the approved HTTPS payment destination; absent means a disabled TWINT button.
- `github_url`: the actual public GitHub repository; absent means an honest publication note.
- `budget`: CHF amounts for donations, hosting, AI and speech. `demo: true` labels all figures as examples and prevents payment activation; this is the checked-in configuration. For actual totals, set `demo: false` and provide an ISO `verified_at` date backed by accounting records. Missing values show a dash, never zero. Spending is calculated from the three categories; comparative bars appear with complete demo figures or complete, dated actual figures.

This is a manually updated statement, not an automatic accounting/payment integration. Never put account credentials, donor identities or other private information in this public file. Payment-provider charges must be accounted for when determining the available donated amount.

The page states that Infomaniak supplies the model in Switzerland and ElevenLabs EU hosting is planned but not configured. The preview currently uses the standard ElevenLabs environment. Before use with real care data, resolve residency, retention, consent and access protection; do not present a planned configuration as deployed.

Run `node --test test/donation.test.cjs test/mockup.test.cjs` for configuration safety, rendering state, and existing app regression checks.
