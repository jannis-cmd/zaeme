import unittest
import os
import tempfile
from unittest.mock import patch

import model_client


class ModelClientTests(unittest.TestCase):
    def test_infomaniak_requires_key_and_model_id_for_ready_status(self):
        with patch.dict(os.environ, {
            "ZAEME_MODEL_URL": "https://api.infomaniak.com/2/ai/123/openai",
            "ZAEME_MODEL_ID": "google/gemma-4-31B-it",
        }, clear=True):
            self.assertFalse(model_client.model_ready())
            with self.assertRaisesRegex(model_client.ModelUnavailable, "Zugangsschlüssel"):
                model_client.call_model([{"role": "user", "content": "Hallo"}])

    def test_infomaniak_key_can_be_read_from_secret_file(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as secret:
            secret.write("synthetic-test-key\n")
            secret.flush()
            with patch.dict(os.environ, {
                "ZAEME_MODEL_URL": "https://api.infomaniak.com/2/ai/123/openai",
                "ZAEME_MODEL_ID": "google/gemma-4-31B-it",
                "ZAEME_MODEL_API_KEY_FILE": secret.name,
            }, clear=True):
                self.assertTrue(model_client.model_ready())
                self.assertEqual(model_client.model_api_key(), "synthetic-test-key")

    def test_persona_compiles_only_supplied_notes(self):
        with patch.object(
            model_client,
            "call_model",
            return_value='{"summary":"Ruth mag ihren Garten.","fields":{"name":"Ruth","age":"81"}}',
        ) as call:
            result = model_client.compile_persona(
                {"profile": {"notes": ["Ruth mag ihren Garten."]}}
            )
        self.assertEqual(result["summary"], "Ruth mag ihren Garten.")
        self.assertIn("Ruth mag ihren Garten.", call.call_args.args[0][1]["content"])

    def test_persona_requires_memory(self):
        with self.assertRaisesRegex(ValueError, "Erinnerung"):
            model_client.compile_persona({"profile": {"notes": []}})

    def test_persona_passages_keep_chat_summary_and_bounded_content(self):
        with patch.object(model_client, "call_model", return_value='{"passages":[{"title":"Was ich mag","text":"Ich mag meinen Garten."},{"title":"Meine Familie","text":"Meine Tochter heisst Anna."}],"fields":{}}'):
            result = model_client.compile_persona({"profile": {"notes": ["Ruth mag ihren Garten. Ihre Tochter heisst Anna."]}})
        self.assertEqual(len(result["passages"]), 2)
        self.assertEqual(result["summary"], "Ich mag meinen Garten. Meine Tochter heisst Anna.")

    def test_persona_rejects_non_object_json(self):
        with patch.object(model_client, "call_model", return_value='[1,2]'):
            with self.assertRaises(model_client.ModelUnavailable):
                model_client.compile_persona({"profile": {"notes": ["Garten"]}})

    def test_bounded_passages_end_at_sentence_or_word_boundary(self):
        self.assertEqual(model_client.bounded_prose("Ich mag Blumen. Ich liebe den Frühling.", 25), "Ich mag Blumen.")
        self.assertEqual(model_client.bounded_prose("Ein sehr langer Satz ohne Ende", 18), "Ein sehr langer …")

    def test_chat_requires_user_message(self):
        with self.assertRaisesRegex(ValueError, "gesprochene Nachricht"):
            model_client.chat({"profile": {}, "messages": []})

    def test_group_chat_keeps_present_profiles_separate_without_speaker_guessing(self):
        with patch.object(model_client, "call_model", return_value="Schön, dass ihr da seid.") as call:
            model_client.chat({"profiles": [{"name": "Hilde", "compiled": "Mag Blumen."}, {"name": "Ruth", "compiled": "Mag Musik."}], "messages": [{"role": "user", "content": "Hallo"}]})
        messages = call.call_args.args[0]
        self.assertIn("Es gibt keine Sprechererkennung", messages[0]["content"])
        self.assertIn('"name": "Hilde"', messages[1]["content"])
        self.assertIn('"name": "Ruth"', messages[1]["content"])

    def test_group_chat_rejects_empty_or_oversized_selection(self):
        for profiles in [[], [{}, {}, {}, {}], "Hilde"]:
            with self.assertRaises(ValueError):
                model_client.chat({"profiles": profiles})

    def test_chat_uses_flexible_length_and_one_question_guidance(self):
        with patch.object(model_client, "call_model", return_value="Gerne.") as call:
            model_client.chat({"profile": {}, "messages": [{"role": "user", "content": "Erzähl mir mehr."}]})
        rules = call.call_args.args[0][0]["content"]
        self.assertNotIn("ein bis zwei kurze Sätze", rules)
        self.assertIn("Tempo und den Wünschen der Person", rules)
        self.assertIn("Stelle höchstens eine sanfte Frage auf einmal", rules)


if __name__ == "__main__":
    unittest.main()
