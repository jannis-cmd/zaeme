import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from gateway import Gateway


class VoiceGatewayTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), lambda *args, **kwargs: Gateway(*args, directory=".", **kwargs)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, route, body, content_type):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request("POST", route, body, {"Content-Type": content_type})
        response = connection.getresponse()
        result = response.status, response.read(), response.getheader("Content-Type")
        connection.close()
        return result

    def test_static_routes_do_not_expose_source_dotfiles_or_directories(self):
        for method in ("GET", "HEAD"):
            for route in ("/model_client.py", "/.env.example", "/%2eenv", "/assets/", "/icons/../gateway.py", "/node_modules/package.json"):
                connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
                connection.request(method, route)
                response = connection.getresponse()
                self.assertEqual(response.status, 404, (method, route))
                response.read()
                connection.close()
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request("GET", "/index.html")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        response.read()
        connection.close()

    def test_voice_note_reaches_adapter_and_returns_text(self):
        boundary = "test-boundary"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"note.webm\"\r\n"
            "Content-Type: audio/webm\r\n\r\n"
        ).encode() + b"synthetic audio" + f"\r\n--{boundary}--\r\n".encode()
        with patch("gateway.transcribe", return_value="Grüezi") as adapter:
            status, raw, _ = self.post(
                "/api/transcribe", body, f"multipart/form-data; boundary={boundary}"
            )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {"text": "Grüezi"})
        adapter.assert_called_once_with(b"synthetic audio", "audio/webm")

    def test_speech_returns_audio(self):
        with patch("gateway.synthesize", return_value=b"synthetic mp3") as adapter:
            status, raw, content_type = self.post(
                "/api/speak", b'{"text":"Guten Tag"}', "application/json"
            )
        self.assertEqual((status, raw, content_type), (200, b"synthetic mp3", "audio/mpeg"))
        adapter.assert_called_once_with("Guten Tag", "male")

    def test_realtime_token_is_short_lived_and_server_minted(self):
        with patch("gateway.realtime_token", return_value="synthetic-token") as adapter:
            status, raw, _ = self.post("/api/scribe-token", b"{}", "application/json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {"token": "synthetic-token"})
        adapter.assert_called_once()

    def test_voice_choice_is_allowlisted(self):
        with patch("gateway.synthesize", return_value=b"mp3") as adapter:
            status, _, _ = self.post("/api/speak", b'{"text":"Hallo","voice":"female"}', "application/json")
        self.assertEqual(status, 200)
        adapter.assert_called_once_with("Hallo", "female")
        status, _, _ = self.post("/api/speak", b'{"text":"Hallo","voice":"custom-id"}', "application/json")
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
