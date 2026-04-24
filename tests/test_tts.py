import pytest
from unittest.mock import patch, MagicMock, call
from src import tts


def test_speak_does_nothing_when_disabled(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": False, "provider": "elevenlabs", "voice_id": "abc",
        "elevenlabs_api_key": "sk-test", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_post = mocker.patch("src.tts.requests.post")
    tts.speak("Hello world, this is a test.")
    mock_post.assert_not_called()


def test_speak_does_nothing_for_empty_text(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "abc",
        "elevenlabs_api_key": "sk-test", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_post = mocker.patch("src.tts.requests.post")
    tts.speak("   ")
    mock_post.assert_not_called()


def test_speak_calls_elevenlabs_with_correct_params(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "voice-abc",
        "elevenlabs_api_key": "sk-test-key", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"mp3data"
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This is a test sentence for the voice system.")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "voice-abc" in call_kwargs[0][0]
    assert call_kwargs[1]["headers"]["xi-api-key"] == "sk-test-key"
    assert "This is a test sentence" in call_kwargs[1]["json"]["text"]


def test_speak_enqueues_audio_bytes(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "elevenlabs", "voice_id": "v1",
        "elevenlabs_api_key": "sk-x", "openai_api_key": "",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"fakemp3"
    mocker.patch("src.tts.requests.post", return_value=mock_response)
    mock_play = mocker.patch("src.tts._play_audio")

    tts.speak("The quick brown fox jumps over the lazy dog.")
    tts._audio_queue.join()

    mock_play.assert_called_once_with(b"fakemp3")


def test_list_voices_returns_name_and_id(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "voices": [
            {"voice_id": "id1", "name": "Rachel"},
            {"voice_id": "id2", "name": "Adam"},
        ]
    }
    mocker.patch("src.tts.config.load", return_value={
        "provider": "elevenlabs", "elevenlabs_api_key": "sk-test", "openai_api_key": ""
    })
    mocker.patch("src.tts.requests.get", return_value=mock_response)

    voices = tts.list_voices()

    assert len(voices) == 2
    assert voices[0] == {"voice_id": "id1", "name": "Rachel"}
    assert voices[1] == {"voice_id": "id2", "name": "Adam"}


def test_speak_routes_to_openai_when_provider_is_openai(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "openai", "voice_id": "v1",
        "elevenlabs_api_key": "", "openai_api_key": "sk-oai",
        "openai_voice": "nova", "openai_model": "tts-1",
    })
    mock_response = MagicMock()
    mock_response.content = b"oaiaudio"
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This sentence is long enough to be spoken aloud.")

    call_url = mock_post.call_args[0][0]
    assert "openai.com" in call_url
    assert mock_post.call_args[1]["json"]["voice"] == "nova"


def test_list_voices_returns_openai_fixed_voices(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "provider": "openai", "elevenlabs_api_key": "", "openai_api_key": "sk-oai"
    })
    voices = tts.list_voices(provider="openai")
    assert len(voices) == 6
    names = [v["name"] for v in voices]
    assert "Nova" in names


def test_speak_routes_to_google_when_provider_is_google(mocker):
    mocker.patch("src.tts.config.load", return_value={
        "enabled": True, "provider": "google", "voice_id": "v1",
        "elevenlabs_api_key": "", "openai_api_key": "",
        "google_api_key": "AIza-test", "google_voice": "en-US-Neural2-C",
    })
    import base64
    fake_audio = base64.b64encode(b"fakemp3").decode()
    mock_response = MagicMock()
    mock_response.json.return_value = {"audioContent": fake_audio}
    mock_post = mocker.patch("src.tts.requests.post", return_value=mock_response)
    mocker.patch("src.tts._play_audio")

    tts.speak("This sentence is long enough to be spoken aloud.")

    call_url = mock_post.call_args[0][0]
    assert "texttospeech.googleapis.com" in call_url

def test_list_voices_returns_google_neural2_only(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "voices": [
            {"name": "en-US-Neural2-A", "ssmlGender": "MALE"},
            {"name": "en-US-Neural2-C", "ssmlGender": "FEMALE"},
            {"name": "en-US-Standard-A", "ssmlGender": "MALE"},
        ]
    }
    mocker.patch("src.tts.requests.get", return_value=mock_response)
    voices = tts.list_voices(provider="google", api_key="AIza-test")
    assert len(voices) == 2
    assert all("Neural2" in v["voice_id"] for v in voices)
    assert not any("Standard" in v["voice_id"] for v in voices)

def test_list_voices_elevenlabs_filters_premade_by_default(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"voices": [
        {"voice_id": "id1", "name": "Rachel"},
        {"voice_id": "id2", "name": "Adam"},
    ]}
    mock_get = mocker.patch("src.tts.requests.get", return_value=mock_response)
    tts.list_voices(provider="elevenlabs", api_key="sk-test")
    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["category"] == "premade"

def test_list_voices_elevenlabs_all_skips_category_filter(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {"voices": []}
    mock_get = mocker.patch("src.tts.requests.get", return_value=mock_response)
    tts.list_voices(provider="elevenlabs", api_key="sk-test", premade_only=False)
    call_kwargs = mock_get.call_args
    assert "category" not in call_kwargs[1].get("params", {})
