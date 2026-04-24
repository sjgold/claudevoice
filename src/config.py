import json
from pathlib import Path
from filelock import FileLock

CONFIG_PATH = Path.home() / ".claude" / "voice-config.json"

_DEFAULTS = {
    "enabled": False,
    "provider": "elevenlabs",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "elevenlabs_api_key": "",
    "openai_api_key": "",
    "openai_voice": "nova",
    "openai_model": "tts-1",
    "google_api_key": "",
    "google_voice": "en-US-Neural2-C",
    "verbosity": "low",
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        return _DEFAULTS.copy()
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _DEFAULTS.copy()
        return {**_DEFAULTS, **data}
    except (json.JSONDecodeError, ValueError):
        return _DEFAULTS.copy()


def save(cfg: dict) -> None:
    import os
    import tempfile
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(CONFIG_PATH) + ".lock")
    with lock:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(cfg, f, indent=2)
            os.replace(tmp_path, CONFIG_PATH)
        except Exception:
            os.unlink(tmp_path)
            raise


def set_enabled(value: bool) -> None:
    cfg = load()
    cfg["enabled"] = value
    save(cfg)


def set_voice(voice_id: str) -> None:
    if not voice_id or not voice_id.strip():
        raise ValueError("voice_id cannot be empty.")
    cfg = load()
    cfg["voice_id"] = voice_id
    save(cfg)


def set_verbosity(level: str) -> None:
    if level not in ("low", "medium", "high"):
        raise ValueError(f"Invalid verbosity: {level!r}. Use low, medium, or high.")
    cfg = load()
    cfg["verbosity"] = level
    save(cfg)


def set_provider(provider: str) -> None:
    if provider not in ("elevenlabs", "openai", "google"):
        raise ValueError(f"Invalid provider: {provider!r}. Use elevenlabs, openai, or google.")
    cfg = load()
    cfg["provider"] = provider
    save(cfg)


def get_provider() -> str:
    return load()["provider"]


def is_enabled() -> bool:
    return load()["enabled"]
