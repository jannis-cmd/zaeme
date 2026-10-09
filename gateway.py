"""Tailnet-only Zäme preview gateway; Modal credentials never reach the browser.

Run with ``.venv/bin/python gateway.py --directory PATH --port 4181``.
This is not a public authentication or data-storage service.
"""

import argparse
import json
import os
from datetime import date
from email import policy
from email.parser import BytesParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from threading import Lock
from urllib.parse import unquote, urlsplit

from elevenlabs_client import TranscriptionUnavailable, api_key, realtime_token, synthesize, transcribe
from model_client import ModelUnavailable, chat, compile_persona, model_ready


MAX_BODY_BYTES = 32_768
MAX_AUDIO_BODY_BYTES = 5 * 1024 * 1024
MAX_DAILY_MODEL_CALLS = 60
MAX_DAILY_TRANSCRIPTIONS = 30
MAX_DAILY_SPEECH_REPLIES = 30
MAX_DAILY_REALTIME_SESSIONS = 12


class Gateway(SimpleHTTPRequestHandler):
    budget_lock = Lock()
    budget_date = None
    budget_used = 0
    transcription_used = 0
    speech_used = 0
    realtime_used = 0

    def setup(self):
        super().setup()
        self.connection.settimeout(65)

    def take_budget(self, counter, maximum):
        with self.budget_lock:
            today = date.today().isoformat()
            if self.budget_date != today:
                type(self).budget_date = today
                for name in ('budget_used', 'transcription_used', 'speech_used', 'realtime_used'):
                    setattr(type(self), name, 0)
            if getattr(self, counter) >= maximum:
                return False
            setattr(type(self), counter, getattr(self, counter) + 1)
            return True

    def send_head(self):
        # Serve frontend files only, never source, secrets or directory listings (also for HEAD).
        path = unquote(urlsplit(self.path).path).lstrip("/") or "index.html"
        legal_pages = {"impressum": "impressum.html", "datenschutz": "datenschutz.html"}
        if path in legal_pages:
            with open(os.path.join(self.directory, legal_pages[path]), "rb") as page:
                body = page.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return BytesIO(body)
        public_files = {"impressum.html", "datenschutz.html", "legal.css", "index.html", "app.js", "styles.css", "capture-worklet.js", "donation.js", "donation.css", "donation.json"}
        asset = path.startswith(("icons/", "fonts/", "assets/")) and path.endswith((".svg", ".png", ".woff2"))
        parts = path.split("/")
        root = os.path.realpath(self.directory)
        target = os.path.realpath(os.path.join(root, path))
        if any(part.startswith(".") for part in parts) or not (path in public_files or asset) or os.path.commonpath([root, target]) != root:
            self.send_error(404)
            return None
        return super().send_head()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/status":
            try:
                voice_key_ready = bool(api_key())
            except TranscriptionUnavailable:
                voice_key_ready = False
            self.send_json(200, {
                "transcription_ready": voice_key_ready,
                "realtime_ready": voice_key_ready,
                "voice_ready": voice_key_ready and bool(os.environ.get("ELEVENLABS_VOICE_ID")),
                "model_ready": model_ready(),
            })
            return
        super().do_GET()

    def do_POST(self):
        route = self.path.split("?", 1)[0]
        if route not in ("/api/persona", "/api/chat", "/api/transcribe", "/api/speak", "/api/scribe-token"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Ungültige Anfrage."})
            return
        limit = MAX_AUDIO_BODY_BYTES if route == "/api/transcribe" else MAX_BODY_BYTES
        if length <= 0 or length > limit:
            self.send_json(413, {"error": "Die Anfrage ist zu gross."})
            return
        try:
            if route == "/api/transcribe":
                self.handle_transcription(length)
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Ungültige Anfrage.")
            if route == "/api/speak":
                self.handle_speech(data)
                return
            if route == "/api/scribe-token":
                self.handle_realtime_token()
                return
            if not self.take_budget('budget_used', MAX_DAILY_MODEL_CALLS):
                self.send_json(429, {"error": "Das Tageslimit für die Vorschau ist erreicht."})
                return
            result = compile_persona(data) if route == "/api/persona" else chat(data)
            self.send_json(200, result)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except ModelUnavailable as exc:
            self.send_json(503, {"error": str(exc)})

    def handle_transcription(self, length):
        if not self.headers.get("Content-Type", "").lower().startswith("multipart/form-data;"):
            self.send_json(400, {"error": "Ungültige Aufnahme."})
            return
        try:
            raw = self.rfile.read(length)
            message = BytesParser(policy=policy.default).parsebytes(
                b"Content-Type: " + self.headers["Content-Type"].encode("ascii")
                + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw
            )
            parts = [part for part in message.iter_parts() if part.get_param("name", header="content-disposition") == "audio"]
            if len(parts) != 1:
                raise ValueError("Eine Aufnahme fehlt.")
            audio = parts[0].get_payload(decode=True)
            mime_type = parts[0].get_content_type()
            if not audio or len(audio) > MAX_AUDIO_BODY_BYTES:
                raise ValueError("Die Aufnahme ist leer oder zu gross.")
            if not self.take_budget('transcription_used', MAX_DAILY_TRANSCRIPTIONS):
                self.send_json(429, {"error": "Das Tageslimit für Aufnahmen ist erreicht."})
                return
            self.send_json(200, {"text": transcribe(audio, mime_type)})
        except (ValueError, UnicodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except TranscriptionUnavailable as exc:
            self.send_json(503, {"error": str(exc)})

    def handle_speech(self, data):
        if data.get("voice", "male") not in ("male", "female"):
            self.send_json(400, {"error": "Diese Stimme ist nicht verfügbar."})
            return
        if not self.take_budget('speech_used', MAX_DAILY_SPEECH_REPLIES):
            self.send_json(429, {"error": "Das Tageslimit für Sprachausgabe ist erreicht."})
            return
        try:
            audio = synthesize(data.get("text"), data.get("voice", "male"))
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except TranscriptionUnavailable as exc:
            self.send_json(503, {"error": str(exc)})
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)

    def handle_realtime_token(self):
        if not self.take_budget('realtime_used', MAX_DAILY_REALTIME_SESSIONS):
            self.send_json(429, {"error": "Das Tageslimit für Live-Gespräche ist erreicht."})
            return
        try:
            self.send_json(200, {"token": realtime_token()})
        except TranscriptionUnavailable as exc:
            self.send_json(503, {"error": str(exc)})

    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # In particular, never log family memories or conversation text.
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4181)
    options = parser.parse_args()

    def handler(*args, **kwargs):
        return Gateway(*args, directory=options.directory, **kwargs)

    server = ThreadingHTTPServer((options.host, options.port), handler)
    print(f"Zäme gateway listening on {options.host}:{options.port}", flush=True)
    server.serve_forever()
