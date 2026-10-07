# Zäme

Zäme is an open-source prototype of a gentle voice companion for people living with memory difficulties. Its primary screen has one large conversation button. A separate family screen holds profiles and short, editable memories. It is **not** a medical device, a substitute for human care, or an emergency service.

The current website is an **interactive guest-mode prototype**. Profiles and text memories work locally. The “Wer bin ich?” refresh and the main voice conversation call a same-origin gateway when it is running and configured. ElevenLabs voice-note transcription and speech playback need a server-side API key and a selected voice. The static-only preview cannot handle API calls. Login and payments are not connected.

## Run the website

```sh
python3 -m http.server 4181 --bind 127.0.0.1
```

Open `http://127.0.0.1:4181/`. This static preview has no voice/model functionality. Do not expose `http.server` publicly: it serves the entire working directory. The checked-in HTML, CSS, JavaScript, local font files, and Iconoir SVGs need no build step. Use any other available local port if 4181 is in use.

For the local voice-enabled preview, export the provider variables shown in `.env.example` (the app does not automatically load `.env`), then run:

```sh
python3 gateway.py --directory . --host 127.0.0.1 --port 4181
```

The gateway uses the Python standard library; Python 3.11+ is recommended. Modal is optional and requires its own installed CLI/account. `HEARTH_ACCESS_CODE` in the example belongs only to the older `backend.py`, not to the current gateway. See [SECURITY.md](SECURITY.md) before deploying.

Interaction tests use jsdom as a development-only dependency:

```sh
npm ci
npm test
```

The first visit starts without a profile. Older preview data is migrated without retaining the fictional default profile; profiles the user created or edited are kept. The app keeps its original `hearth.guest.v3` browser storage key after the rename, so existing profiles and memories survive. A previously selected named profile remains active on reload; otherwise the first saved named profile is selected automatically. The family screen has a direct return to the conversation screen. In guest mode you can:

- Create, choose, edit, and delete up to three local profiles. Tap booklets to select/deselect multiple people who are present; selected people appear first. Each named selected profile is sent separately to the model with group-conversation rules. There is no speaker identification, and changing the selection resets conversation context. An explicitly empty selection stays empty on reload.
- Add, edit, and delete up to twelve text memories per profile, displayed newest first. Adding a thirteenth removes the oldest. The browser warns when this happens.
- Edit fixed profile fields. They autosave to browser `localStorage`.
- Record and discard a voice note locally. Confirming it sends the audio to the same-origin `api/transcribe` route; with the configured gateway, ElevenLabs Scribe v2 returns editable text to the composer. Saving that text as a memory is a separate action. The static-only preview cannot transcribe. Do not use identifiable recordings in the preview.
- Tap the main button once to start a live conversation and again to end it. ElevenLabs Scribe v2 Realtime shows partial captions and detects a completed turn after a pause; a replaceable model API composes a short reply, ElevenLabs speaks it in Standard German, and listening resumes automatically. The family screen has a global female/male voice choice. Conversation history stays in memory for the active browser tab only and is never copied into the saved profile or memories. The reply remains visible as text if voice playback fails. In the static preview, no conversation is sent.

There is no account synchronization. Clearing this browser's site data removes local profiles. The planned guest conversation allowance is five successful turns per day; failed mockup attempts are not counted. This client-side limit is illustrative, not abuse protection.

## What is not connected yet

- A configured live model API is still required for persona compilation. The original notes remain the source of truth. Editing, deleting, or expiring a note invalidates any derived summary.
- Production-safe voice service and a validated Swiss German experience. The private preview currently uses Infomaniak Gemma 4 for text and ElevenLabs for audio, but this does not make it suitable for identifiable care data or public access. A fresh installation needs its own provider credentials.
- Login and cross-device storage.
- TWINT donations or a live budget. The donation page currently shows explicitly labelled demo figures, not actual donations or costs. Payments stay disabled in demo mode. EU residency for ElevenLabs is planned, not configured.

`modal_gguf.py` defines a private, scale-to-zero Modal llama.cpp server for the verified GGUF and remains an optional backend; Modal could instead be used for later adapter training. `model_client.py` talks to any compatible `/v1/chat/completions` API. For Infomaniak AI Services, use `ZAEME_MODEL_URL=https://api.infomaniak.com/2/ai/<product_id>/openai` and `ZAEME_MODEL_ID=google/gemma-4-31B-it`. Put the Infomaniak bearer token in a file outside the repository and set `ZAEME_MODEL_API_KEY_FILE` to its absolute path; alternatively set `ZAEME_MODEL_API_KEY` in the server environment. The product ID and API token are available after activating AI Services in Infomaniak Manager. Set an Infomaniak spending limit before using real traffic (the current minimum is CHF 20/month). The old private Modal endpoint can still use `ZAEME_MODAL_PROXY_TOKEN` or the authenticated Modal CLI. `gateway.py` serves the webapp and routes `/api/persona`, `/api/chat`, `/api/transcribe`, `/api/scribe-token`, and `/api/speak` from the same origin. No GGUF, token, or identifiable family data is checked into this project. To enable voice notes and live conversation, set `ELEVENLABS_API_KEY` server-side or point `ELEVENLABS_API_KEY_FILE` to an owner-readable secret file. `/api/speak` additionally requires `ELEVENLABS_VOICE_ID` (male); the female voice defaults to Sarah and can be changed with `ELEVENLABS_FEMALE_VOICE_ID`. Speech uses German `eleven_flash_v2_5` at low-bitrate MP3. The browser only receives a one-use, short-lived Scribe token; the long-lived key stays server-side. Run `.venv/bin/python gateway.py --directory . --host 127.0.0.1 --port 4181`. Never put credentials in the webapp. The gateway's in-memory daily caps and the provider-side spending cap are only preview cost guards, not authentication or production abuse protection.

Scribe v2 lists **German**, not Swiss German as a separate guaranteed language. The adapter leaves language detection on so Swiss German and mixed-language notes can be tested, and returns the raw transcript for human correction; do not assume dialect accuracy. ElevenLabs' standard account stores customer data in the US; EU residency and zero-retention are Enterprise features. The current Free account is therefore unsuitable for identifiable care recordings or family memories. Use synthetic/consented test material only until consent, data handling, access control, and retention are resolved.

`backend.py` is an **earlier standalone Modal + Qwen + ElevenLabs prototype**, not wired to this mockup. It remains as a reference; do not deploy it as a public service without individual authentication, rate limiting, cost controls, privacy review, and endpoint compatibility work. `eval_cases.json` and `evaluate.py` are also from that prototype.

The intended backend boundary is a stable app API with interchangeable model providers; Modal is the first provider for the workshop challenge. ElevenLabs supplies transcription and speech. API credentials must stay server-side. Real accounts, donations, and derived personas require a server and database, not only browser storage.

## Design and licensing

The palette takes its colours from [Demenzfreundlich Kreis 6](https://demenzfreundlich-kreis6.ch/). Partner logos for Demenzfreundlich Kreis 6 and MYNA are bundled with permission confirmed by the project owner. These marks are not covered by the source-code MIT licence; see [assets/NOTICE.md](assets/NOTICE.md). Interface icons are from [Iconoir](https://iconoir.com/) under its [MIT license](icons/LICENSE). The self-hosted Nunito Sans files are covered by their [font license](fonts/LICENSE.txt).

Source code is under the [MIT license](LICENSE). There are no proprietary frontend packages, no trackers, and no committed credentials. Contributions should preserve the distinction between verified profile facts and model-generated suggestions, and between real financial data and placeholders.

Before any use with real people or identifiable care information, involve people living with dementia and care partners in testing, assess accessibility and consent, and complete a privacy/security review. See the original [Alzheimer's Society communication guidance](https://www.alzheimers.org.uk/about-dementia/stages-and-symptoms/dementia-symptoms/how-to-communicate-dementia) for the conversational principles behind the earlier backend prompt.
