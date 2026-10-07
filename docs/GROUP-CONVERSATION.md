# Group conversation debug — 7 October 2026

The reported two-person conversations reached ElevenLabs with two separate profiles and the group rules. The later test also contained both profiles' guidance and compiled summaries. Later provider usage records reused the prompt prefix; they did not indicate that it disappeared after the first turn.

A synthetic test through the configured ElevenLabs agent completed four user turns. In the fourth answer it still recalled Otto's interest in railways and the Verkehrshaus. In preceding turns it used Marta's gardening preference and Otto's train journeys. This verifies profile availability beyond the first turn for that test; it is not a guarantee of every future model response.

The reproduced behavior problem was passive, generic questioning and answering when a person addressed another participant. The former rules described caution and attribution, but gave little direction for facilitating a shared conversation.

## Changes

- The main prompt asks Zäme to speak like a familiar acquaintance, proactively using supplied stories and preferences, and to build on them throughout the conversation. Existing instructions prohibit invented biography or shared experiences.
- Group rules distinguish Zäme from the humans, retain each person's facts and address, suggest a specific known topic, and invite the other person without inventing shared preferences or relationships.
- Group greetings name the selected people. One-person greetings retain their existing wording.
- The agent has ElevenLabs' `skip_turn` system tool, so it can yield without narrating stage directions. The classic fallback also supports a silent tool result and returns to listening without TTS.
- Bounded saved memories are included alongside guidance and summaries. They are available even before a new summary is generated. Group data are sent separately for each person.

## Verification

Python regression tests cover later-turn profile retention, separate uncompiled memories, greetings and silent tool results. The browser regression checks that silent results do not trigger speech and resume listening.

`experiments/group-conversation/evaluate.py` runs ten manual model checks with fictional Marta and Otto: initiative, later preference use, later profile recall, direct address, passing a question to another participant, keeping a family fact attached to its own profile, short answers, a new topic after silence, repeated silence, and an explicit request for quiet. It uses the preview's `ZAEME_MODEL_*` configuration and makes model API calls. Inspect the responses for behavior rather than treating keyword matches as a conversation-quality score.

The live checks returned a specific gardening invitation, a later train-travel question, correct railway/Verkehrshaus recall, a silent `skip_turn`, a question directed to Otto, and no transfer of Marta's family fact to Otto.

There is still no speaker identification. A named addressee is not evidence of who spoke. Explicit self-identification applies to that utterance; a later speaker may be someone else. These changes improve facilitation without claiming voice recognition.

## Keeping the conversation moving

The prompt favors short contributions and concrete, personal, easy questions, optionally offering two simple alternatives. Zäme follows what someone says, rather than running a question list or asking again for known preferences.

The main ElevenLabs agent uses its existing `turn_timeout=30` and patient turn-taking. After a long pause, the prompt asks it to offer one different profile topic. After continued silence it should use `skip_turn`, and an explicit request for quiet takes precedence. This reuses provider turn-taking instead of adding a competing browser timer. The existing 120-second silence end limit and ten-minute session limit remain in place. The classic fallback receives the same conversational wording, but does not have an automatic idle-topic trigger.

Synthetic model checks yielded a concrete two-color choice for tulips, a railway question after silence, and silent tool results both after another unanswered topic and after a request for quiet. Model checks are distinct from testing the real audio timeout.

A live voice-mode WebSocket test with silent PCM input also triggered re-engagement after the configured idle period. After an explicit request for quiet, no further spoken response arrived during a 40-second observation. The first re-engagement was too general; the final prompt was tightened to start a profile topic directly rather than asking whether people want to continue talking.
