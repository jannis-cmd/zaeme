# Zäme · Development guide

[← Project overview / Projektübersicht](../README.md)

Run all commands below from the repository root.

Zäme is an open-source prototype of a gentle voice companion for people living with memory difficulties. Its primary screen has one large conversation button. A separate family screen holds profiles and short, editable memories. It is **not** a medical device, a substitute for human care, or an emergency service.

The current website is an **interactive prototype with a hosted account service**. Profiles and text memories work locally. **ElevenLabs Agents is the default conversation mode**, with Infomaniak as its custom LLM. The original Scribe → Infomaniak → speech pipeline remains an automatic budget/unavailability fallback and can also be run explicitly. The hosted entry point adds ZITADEL login and a server-enforced guest trial; see [ZITADEL deployment](ZITADEL-LOGIN.md). Payments are not connected.

## Run the website

```sh
python3 -m http.server 4181 --bind 127.0.0.1
```

Open `http://127.0.0.1:4181/`. This static preview has no voice/model functionality. Do not expose `http.server` publicly: it serves the entire working directory. The checked-in HTML, CSS, JavaScript, local font files, and Iconoir SVGs need no build step. Use any other available local port if 4181 is in use.

For the main voice-enabled preview, export the provider variables shown in `.env.example` (the app does not automatically load `.env`), then run:

```sh
npm ci
npm run build
# Once: creates/updates a private agent and stores the Infomaniak key
# in ElevenLabs as a custom-LLM secret. Requires provider credentials.
python3 agents_service.py --setup
python3 agents_gateway.py --directory . --port 4185
```

Open `http://127.0.0.1:4185/`. The browser SDK is bundled locally; no credentials enter the bundle. Rebuild after changing `voice-agent.js`. Generated `dist/` files are ignored by Git.

The agent uses the same compact system rules, selected profiles, compiled summaries and bounded saved memory bubbles as the fallback. Agent history is managed by ElevenLabs; the classic fallback sends the last eight messages. Neither mode adds facts to profiles or memories automatically.

Set an explicit monthly app budget with `ZAEME_AGENTS_MONTHLY_MINUTES` (positive whole minutes), or `monthly_agent_minutes` in the external Agent configuration JSON. Environment configuration takes precedence. No subscription tier or allowance is hardcoded: check your own account and choose a suitable limit. Missing/invalid configuration or unavailable usage switches new sessions to classic mode. The guard supports monthly billing cycles, reserves a full ten-minute session and keeps a one-minute buffer. It counts workspace-wide Agent usage and uses a durable ledger to cover reporting delays. This is a conservative preview guard, not a guaranteed billing cap. The fallback has separate transcription, TTS and model costs. Agent call queueing is disabled: when the single conversation slot is busy, the existing unavailable message is shown instead of hold music.

To force classic mode, run `python3 agents_gateway.py --backend classic --directory . --port 4185`, or use `gateway.py` directly. Install the pinned dependencies in `requirements-web.txt`; Python 3.12+ is recommended. Modal is optional and requires its SDK separately. See [SECURITY.md](../SECURITY.md) before deploying. Both gateways bind to loopback by default.


Interaction tests use jsdom as a development-only dependency:

```sh
npm ci
npm test
python3 -m pip install -r requirements-web.txt
python3 -m unittest discover -s test -p 'test_*.py'
```

The first visit starts without a profile. Older preview data is migrated without retaining the fictional default profile; profiles the user created or edited are kept. The app keeps its original `hearth.guest.v3` browser storage key after the rename, so existing profiles and memories survive. A previously selected named profile remains active on reload; otherwise the first saved named profile is selected automatically. The family screen has a direct return to the conversation screen. In the standalone static preview you can (the hosted guest trial allows one person; accounts have no person-count quota):

- Create, choose, edit, and delete up to three local profiles. Tap booklets to select/deselect multiple people who are present; selected people appear first. Each named selected profile, including bounded saved memories, is sent separately to the model with group-conversation rules. Zäme proactively uses known interests and can yield silently when someone addresses another participant. See [group conversation diagnostics](GROUP-CONVERSATION.md). There is no speaker identification, and changing the selection resets conversation context. An explicitly empty selection stays empty on reload.
- Add, edit, and delete up to twelve text memories per profile, displayed newest first. Adding a thirteenth removes the oldest. The browser warns when this happens.
- Edit fixed profile fields. They autosave to browser `localStorage`.
- Record and discard a voice note locally. Confirming it sends the audio to the same-origin `api/transcribe` route; with the configured gateway, ElevenLabs Scribe v2 returns editable text to the composer. Saving that text as a memory is a separate action. The static-only preview cannot transcribe. Do not use identifiable recordings in the preview.
- Tap the main button once to start a live conversation and again to end it. ElevenLabs Agents manages listening, turn-taking, interruptions and spoken replies, using Infomaniak for the model. The classic fallback uses Scribe v2 Realtime, the model API, then speech playback, without interruption support. Both modes show captions and use the global female/male voice choice. Conversation content is never copied into saved profiles or memories. In the static preview, no conversation is sent.

There is no account synchronization. Clearing this browser's site data removes local profiles. The standalone preview illustrates five successful turns per day; the hosted guest trial instead grants five total minutes once per browser. In the standalone preview, failed mockup attempts are not counted. This client-side limit is illustrative, not abuse protection.

## Communication principles and evidence

Reviewed on 7 October 2026. The live conversation rules are `CHAT_RULES` in `model_client.py`; `GROUP_RULES` is added for several present people. Sources are documented here, not sent with each request. Profile compilation uses separate rules and is unchanged.

The aim is to help a person feel heard, respected and free from pressure, not to force cheerfulness or promise a therapeutic benefit. The compact prompt translates these principles into instructions:

- Speak to an adult on equal terms, with clear language rather than childish or patronizing speech.
- Acknowledge feelings without endorsing frightening or unsupported claims; avoid arguments and unfounded reassurance.
- Follow the person's interests; use verified memories as invitations, never memory tests or invented shared experiences.
- Keep one thought at a time, adapt length and ask at most one gentle question, not after every answer.
- Respond patiently to repetition; respect silence, reluctance and requests to stop.

### Sources and limits

[Williams et al. (2017), *A Communication Intervention to Reduce Resistiveness in Dementia Care: A Cluster Randomized Controlled Trial*](https://pubmed.ncbi.nlm.nih.gov/27048705/), DOI 10.1093/geront/gnw047: a staff communication intervention in 13 nursing homes reduced elderspeak; changes in elderspeak were associated with changes in resistance to care. This supports avoiding infantilizing communication. It did not test an AI companion, mood improvement from a chatbot, or this prompt.

[Alzheimer's Society, *How to communicate with a person with dementia*](https://www.alzheimers.org.uk/about-dementia/stages-and-symptoms/dementia-symptoms/how-to-communicate-dementia): professional practical guidance, not a clinical trial. It recommends individualized, calm communication, processing time, one idea at a time, fewer questions, listening to feelings and avoiding memory pressure. Our prompt is an adaptation of those recommendations, not a validated intervention.

The distinction between acknowledging feelings and endorsing unsupported claims, and prohibiting fabricated experiences or guarantees, is also an AI-specific safety design choice. A prompt cannot control actual turn-taking pauses, speech recognition or voice tone; those need separate audio-layer testing. Dementia experiences differ: do not assume every strategy fits everyone.

Existing safeguards remain: no medication/dosage advice, no impersonation of relatives or clinicians, no unavailable actions, nearby human support for danger or distress, and no speaker guessing or mixing people's biographies. Zäme is not a substitute for care or emergency help.

Tests check that these instructions reach the model; they do not establish that the model follows them. Before care use, qualified human review and consent-based evaluation are needed, including repeated questions, "I have nothing to say", distress, a deceased relative, medication uncertainty and group conversations. Use fictional scenarios in the preview; do not advertise clinical efficacy.

## What is not connected yet

- A configured live model API is still required for persona compilation. The original notes remain the source of truth. Editing, deleting, or expiring a note invalidates any derived summary.
- Production-safe voice service and a validated Swiss German experience. The private preview currently uses Infomaniak Gemma 4 for text and ElevenLabs for audio, but this does not make it suitable for identifiable care data or public access. A fresh installation needs its own provider credentials.
- Cross-device storage. Hosted login is available through ZITADEL; it separates local account libraries but does not sync them.
- TWINT donations or a live budget. The donation page currently shows explicitly labelled demo figures, not actual donations or costs. Payments stay disabled in demo mode.

`modal_gguf.py` defines a private, scale-to-zero Modal llama.cpp server for a supplied GGUF model and remains an optional backend; Modal could instead be used for later adapter training. `model_client.py` talks to any compatible `/v1/chat/completions` API. For Infomaniak AI Services, use `ZAEME_MODEL_URL=https://api.infomaniak.com/2/ai/<product_id>/openai` and `ZAEME_MODEL_ID=google/gemma-4-31B-it`. Put the Infomaniak bearer token in a file outside the repository and set `ZAEME_MODEL_API_KEY_FILE` to its absolute path; alternatively set `ZAEME_MODEL_API_KEY` in the server environment. The product ID and API token are available after activating AI Services in Infomaniak Manager. Set an Infomaniak spending limit before using real traffic. The old private Modal endpoint can still use `ZAEME_MODAL_PROXY_TOKEN` or the authenticated Modal CLI. `gateway.py` serves the webapp and routes `/api/persona`, `/api/chat`, `/api/transcribe`, `/api/scribe-token`, and `/api/speak` from the same origin. No GGUF, token, or identifiable family data is checked into this project. To enable voice notes and live conversation, set `ELEVENLABS_API_KEY` server-side or point `ELEVENLABS_API_KEY_FILE` to an owner-readable secret file. `/api/speak` additionally requires `ELEVENLABS_VOICE_ID` (male); the female voice defaults to Sarah and can be changed with `ELEVENLABS_FEMALE_VOICE_ID`. Speech uses German `eleven_flash_v2_5` at low-bitrate MP3. The browser only receives a one-use, short-lived Scribe token; the long-lived key stays server-side. Run `.venv/bin/python gateway.py --directory . --host 127.0.0.1 --port 4181`. Never put credentials in the webapp. The gateway's in-memory daily caps and the provider-side spending cap are only preview cost guards, not authentication or production abuse protection.

Scribe v2 lists **German**, not Swiss German as a separate guaranteed language. The adapter leaves language detection on so Swiss German and mixed-language notes can be tested, and returns the transcript for human correction; do not assume dialect accuracy. The preview is not approved for identifiable care data. Agent setup disables audio recording and requests one-day conversation retention; this does not establish zero retention or a residency guarantee. Use fictional test material until consent, data handling, access control and retention are resolved.

The unused standalone Modal/Qwen prototype and its shared-access-code API were removed. Its previous source is available in Git history. The current optional inference adapter, classic conversation fallback and browser-storage migrations remain supported.

The backend boundary is a stable app API with interchangeable model providers. Infomaniak is used for live conversations and persona compilation; Modal remains an optional workshop/training backend. ElevenLabs supplies the default Agent orchestration and the classic transcription/speech services. Credentials stay server-side. The hosted account service is `web_service.py`. Run it in front of the private loopback gateway; never publish either development gateway directly. Donations remain unconnected.

## Design and licensing

The palette takes its colours from [Demenzfreundlich Kreis 6](https://demenzfreundlich-kreis6.ch/). Partner logos for Demenzfreundlich Kreis 6 and MYNA are bundled with permission confirmed by the project owner. These marks are not covered by the source-code MIT licence; see [assets/NOTICE.md](../assets/NOTICE.md). Interface icons are from [Iconoir](https://iconoir.com/) under its [MIT license](../icons/LICENSE). The self-hosted Nunito Sans files are covered by their [font license](../fonts/LICENSE.txt).

Source code is under the [MIT license](../LICENSE). There are no proprietary frontend packages, no trackers, and no committed credentials. Contributions should preserve the distinction between verified profile facts and model-generated suggestions, and between real financial data and placeholders.

Before any use with real people or identifiable care information, involve people living with dementia and care partners in testing, assess accessibility and consent, and complete a privacy/security review. See the original [Alzheimer's Society communication guidance](https://www.alzheimers.org.uk/about-dementia/stages-and-symptoms/dementia-symptoms/how-to-communicate-dementia) for the conversational principles behind the earlier backend prompt.
