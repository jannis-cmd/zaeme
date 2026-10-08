"""Minimal server-side ElevenLabs Scribe adapter for short voice notes."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote
from uuid import uuid4


class TranscriptionUnavailable(Exception):
    pass


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    key_file = os.environ.get("ELEVENLABS_API_KEY_FILE", "").strip()
    if not key and key_file:
        try:
            key = Path(key_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise TranscriptionUnavailable("Der lokale Sprachschlüssel ist nicht lesbar.") from exc
    return key


def transcribe(audio, mime_type):
    key = api_key()
    if not key:
        raise TranscriptionUnavailable("Spracherkennung ist noch nicht eingerichtet.")
    if mime_type not in {"audio/webm", "audio/mp4", "audio/mpeg", "audio/wav", "audio/ogg"}:
        raise ValueError("Dieses Aufnahmeformat wird nicht unterstützt.")
    if not audio:
        raise ValueError("Die Aufnahme war leer.")

    extension = {
        "audio/webm": "webm",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/ogg": "ogg",
    }[mime_type]
    boundary = "zaeme-" + uuid4().hex

    def field(name, value):
        return (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n"
        ).encode("utf-8")

    body = b"".join(
        [
            field("model_id", "scribe_v2"),
            field("tag_audio_events", "false"),
            field("diarize", "false"),
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"aufnahme.{extension}\"\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("ascii"),
            audio,
            f"\r\n--{boundary}--\r\n".encode("ascii"),
        ]
    )
    request = Request(
        "https://api.elevenlabs.io/v1/speech-to-text",
        data=body,
        headers={
            "xi-api-key": key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        # Provider error bodies can contain request details; never return them to clients.
        raise TranscriptionUnavailable(f"ElevenLabs antwortete mit HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TranscriptionUnavailable("Die Spracherkennung ist gerade nicht erreichbar.") from exc
    text = result.get("text") if isinstance(result, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionUnavailable("Es wurden keine Worte erkannt.")
    return text.strip()


def realtime_token():
    key = api_key()
    if not key:
        raise TranscriptionUnavailable("Spracherkennung ist noch nicht eingerichtet.")
    request = Request(
        "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe",
        data=b"{}",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise TranscriptionUnavailable(f"ElevenLabs antwortete mit HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise TranscriptionUnavailable("Die Live-Spracherkennung ist gerade nicht erreichbar.") from exc
    token = result.get("token") if isinstance(result, dict) else None
    if not isinstance(token, str) or not token:
        raise TranscriptionUnavailable("Die Live-Spracherkennung lieferte keinen Zugang.")
    return token


def synthesize(text, voice="male"):
    key = api_key()
    if voice not in ("male", "female"):
        raise ValueError("Diese Stimme ist nicht verfügbar.")
    voice_id = (
        os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
        if voice == "male"
        else os.environ.get("ELEVENLABS_FEMALE_VOICE_ID", "EXAVITQu4vr4xnSDxMaL").strip()
    )
    if not key or not voice_id:
        raise TranscriptionUnavailable("Sprachausgabe ist noch nicht eingerichtet.")
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError("Der Antworttext ist leer oder zu lang.")
    if not voice_id.isalnum():
        raise ValueError("Die Stimmkonfiguration ist ungültig.")
    body = json.dumps(
        {"text": text.strip(), "model_id": "eleven_flash_v2_5", "language_code": "de"},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        "https://api.elevenlabs.io/v1/text-to-speech/"
        + quote(voice_id)
        + "?output_format=mp3_22050_32",
        data=body,
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            audio = response.read(2 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise TranscriptionUnavailable(f"ElevenLabs antwortete mit HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise TranscriptionUnavailable("Die Sprachausgabe ist gerade nicht erreichbar.") from exc
    if not audio or len(audio) > 2 * 1024 * 1024:
        raise TranscriptionUnavailable("Die Sprachausgabe war leer oder zu gross.")
    return audio
