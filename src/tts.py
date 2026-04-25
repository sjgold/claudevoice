import base64
import shutil
import subprocess
import threading
import queue

import requests

from src import config

# Locate ffplay at import time — needed because Claude Code's subprocess PATH
# may not include winget-installed binaries on Windows.
_FFPLAY_FALLBACKS = [
    r"C:\Users\SJG\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-essentials_build\bin\ffplay.exe",
]
_FFPLAY = shutil.which("ffplay") or next(
    (p for p in _FFPLAY_FALLBACKS if shutil.os.path.isfile(p)), "ffplay"
)

_EL_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_EL_VOICES_URL = "https://api.elevenlabs.io/v1/voices"
_OAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_GOOGLE_VOICES_URL = "https://texttospeech.googleapis.com/v1/voices"

OPENAI_VOICES = ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]

_audio_queue: queue.Queue = queue.Queue()
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()


def _play_audio(mp3_bytes: bytes) -> None:
    proc = subprocess.Popen(
        [_FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", "-"],
        stdin=subprocess.PIPE,
    )
    proc.communicate(mp3_bytes)


def _audio_worker() -> None:
    while True:
        item = _audio_queue.get()
        if item is None:
            break
        _play_audio(item)
        _audio_queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_audio_worker, daemon=True)
            _worker.start()


def _speak_elevenlabs(text: str, cfg: dict) -> None:
    resp = requests.post(
        _EL_TTS_URL.format(voice_id=cfg["voice_id"]),
        headers={"xi-api-key": cfg["elevenlabs_api_key"], "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=15,
    )
    resp.raise_for_status()
    _audio_queue.put(resp.content)


def _speak_openai(text: str, cfg: dict) -> None:
    resp = requests.post(
        _OAI_TTS_URL,
        headers={"Authorization": f"Bearer {cfg['openai_api_key']}", "Content-Type": "application/json"},
        json={
            "model": cfg.get("openai_model", "tts-1"),
            "input": text,
            "voice": cfg.get("openai_voice", "nova"),
        },
        timeout=15,
    )
    resp.raise_for_status()
    _audio_queue.put(resp.content)


def _speak_google(text: str, cfg: dict) -> None:
    resp = requests.post(
        f"{_GOOGLE_TTS_URL}?key={cfg['google_api_key']}",
        json={
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": cfg.get("google_voice", "en-US-Neural2-C")},
            "audioConfig": {"audioEncoding": "MP3"},
        },
        timeout=15,
    )
    resp.raise_for_status()
    audio_bytes = base64.b64decode(resp.json()["audioContent"])
    _audio_queue.put(audio_bytes)


def speak(text: str) -> None:
    cfg = config.load()
    if not cfg["enabled"] or not text.strip():
        return
    _ensure_worker()
    provider = cfg.get("provider", "elevenlabs")
    if provider == "openai":
        _speak_openai(text, cfg)
    elif provider == "google":
        _speak_google(text, cfg)
    else:
        _speak_elevenlabs(text, cfg)


def list_voices(provider: str | None = None, api_key: str | None = None, premade_only: bool = True) -> list[dict]:
    cfg = config.load()
    provider = provider or cfg.get("provider", "elevenlabs")
    if provider == "openai":
        return [{"voice_id": v, "name": v.capitalize()} for v in OPENAI_VOICES]
    if provider == "google":
        key = api_key or cfg["google_api_key"]
        resp = requests.get(
            f"{_GOOGLE_VOICES_URL}?key={key}&languageCode=en-US",
            timeout=10,
        )
        resp.raise_for_status()
        voices = [
            v for v in resp.json()["voices"]
            if "Neural2" in v["name"]
        ]
        return [{"voice_id": v["name"], "name": v["name"]} for v in sorted(voices, key=lambda x: x["name"])]
    # ElevenLabs
    key = api_key or cfg["elevenlabs_api_key"]
    params = {}
    if premade_only:
        params["category"] = "premade"
    resp = requests.get(
        _EL_VOICES_URL,
        headers={"xi-api-key": key},
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    return [{"voice_id": v["voice_id"], "name": v["name"]} for v in resp.json()["voices"]]
