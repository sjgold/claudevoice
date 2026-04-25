import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_load_returns_defaults_when_no_file(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["enabled"] is False
    assert cfg["provider"] == "elevenlabs"
    assert cfg["voice_id"] == "EXAVITQu4vr4xnSDxMaL"
    assert cfg["elevenlabs_api_key"] == ""
    assert cfg["openai_api_key"] == ""
    assert cfg["openai_voice"] == "nova"
    assert cfg["openai_model"] == "tts-1"
    assert cfg["google_api_key"] == ""
    assert cfg["google_voice"] == "en-US-Neural2-C"
    assert cfg["verbosity"] == "2"


def test_save_and_load_roundtrip(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.save({"enabled": True, "provider": "openai", "voice_id": "abc123", "elevenlabs_api_key": "sk-test", "openai_api_key": "sk-oai", "openai_voice": "nova", "openai_model": "tts-1", "google_api_key": "", "google_voice": "en-US-Neural2-C", "verbosity": "2"})
        cfg = config.load()
    assert cfg["enabled"] is True
    assert cfg["provider"] == "openai"
    assert cfg["elevenlabs_api_key"] == "sk-test"


def test_set_enabled_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_enabled(True)
        assert config.is_enabled() is True
        config.set_enabled(False)
        assert config.is_enabled() is False


def test_verbosity_defaults_to_2(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["verbosity"] == "2"


def test_set_verbosity_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_verbosity("2")
        cfg = config.load()
    assert cfg["verbosity"] == "2"


def test_set_voice_persists_across_reload(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_voice("voice-xyz-789")
        cfg = config.load()
    assert cfg["voice_id"] == "voice-xyz-789"


def test_load_merges_missing_keys(tmp_path):
    config_path = tmp_path / "voice-config.json"
    config_path.write_text(json.dumps({"elevenlabs_api_key": "sk-existing"}))
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["elevenlabs_api_key"] == "sk-existing"
    assert cfg["enabled"] is False
    assert cfg["voice_id"] == "EXAVITQu4vr4xnSDxMaL"
    assert cfg["google_api_key"] == ""
    assert cfg["openai_voice"] == "nova"


def test_provider_defaults_to_elevenlabs(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["provider"] == "elevenlabs"


def test_set_provider_persists(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_provider("openai")
        assert config.get_provider() == "openai"


def test_set_provider_rejects_invalid(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        with pytest.raises(ValueError):
            config.set_provider("amazon")


def test_set_provider_accepts_google(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        config.set_provider("google")
        assert config.get_provider() == "google"


def test_google_defaults_present(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["google_api_key"] == ""
    assert cfg["google_voice"] == "en-US-Neural2-C"


def test_load_handles_corrupt_json(tmp_path):
    config_path = tmp_path / "voice-config.json"
    config_path.write_text("this is not json {{{")
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["enabled"] is False
    assert cfg["provider"] == "elevenlabs"


def test_load_handles_empty_file(tmp_path):
    config_path = tmp_path / "voice-config.json"
    config_path.write_text("")
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        cfg = config.load()
    assert cfg["enabled"] is False


def test_set_verbosity_rejects_invalid(tmp_path):
    config_path = tmp_path / "voice-config.json"
    with patch("src.config.CONFIG_PATH", config_path):
        from src import config
        with pytest.raises(ValueError):
            config.set_verbosity("extreme")
