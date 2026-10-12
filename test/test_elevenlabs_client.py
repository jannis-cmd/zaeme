import io
import json
import unittest
from unittest.mock import patch

import elevenlabs_client


class ElevenLabsClientTests(unittest.TestCase):
    def test_realtime_token_keeps_private_key_server_side(self):
        response = io.BytesIO(json.dumps({"token": "one-use-test-token"}).encode())
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "private-test-key"}):
            with patch.object(elevenlabs_client, "urlopen", return_value=response) as call:
                token = elevenlabs_client.realtime_token()
        self.assertEqual(token, "one-use-test-token")
        request = call.call_args.args[0]
        self.assertIn("single-use-token/realtime_scribe", request.full_url)
        self.assertEqual(request.get_header("Xi-api-key"), "private-test-key")

    def test_transcription_keeps_key_server_side_and_uses_scribe(self):
        response = io.BytesIO(json.dumps({"text": "Grüezi mitenand"}).encode())
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "private-test-key"}):
            with patch.object(elevenlabs_client, "urlopen", return_value=response) as call:
                text = elevenlabs_client.transcribe(b"synthetic-audio", "audio/webm")
        self.assertEqual(text, "Grüezi mitenand")
        request = call.call_args.args[0]
        self.assertEqual(request.get_header("Xi-api-key"), "private-test-key")
        self.assertIn(b'scribe_v2', request.data)
        self.assertIn(b'name="file"', request.data)
        self.assertNotIn(b"private-test-key", request.data)

    def test_speech_uses_german_flash_and_configured_voice(self):
        with patch.dict(
            "os.environ",
            {"ELEVENLABS_API_KEY": "private-test-key", "ELEVENLABS_VOICE_ID": "abc123"},
        ):
            with patch.object(elevenlabs_client, "urlopen", return_value=io.BytesIO(b"mp3")) as call:
                audio = elevenlabs_client.synthesize("Guten Tag")
        self.assertEqual(audio, b"mp3")
        request = call.call_args.args[0]
        self.assertIn("/abc123?", request.full_url)
        self.assertEqual(json.loads(request.data)["model_id"], "eleven_flash_v2_5")
        self.assertEqual(json.loads(request.data)["language_code"], "de")

    def test_missing_key_does_not_make_request(self):
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": ""}):
            with patch.object(elevenlabs_client, "urlopen") as call:
                with self.assertRaises(elevenlabs_client.TranscriptionUnavailable):
                    elevenlabs_client.transcribe(b"audio", "audio/webm")
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
