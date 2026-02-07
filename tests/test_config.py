"""Tests for configuration system."""

from pathlib import Path

from agentkit.config import Config


def test_load_config_defaults():
    config = Config(profile="test")
    assert config.profile == "test"
    assert config.model == "claude-opus-4-6"


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    config = Config(profile="test")
    assert config.telegram_bot_token == "tok123"
    assert config.telegram_chat_id == "chat456"


def test_profile_dir(tmp_path):
    config = Config(profile="myprofile", project_root=tmp_path)
    assert config.profile_dir == tmp_path / "profiles" / "myprofile"


def test_model_always_opus():
    config = Config(profile="test")
    assert config.model == "claude-opus-4-6"
    # model is not settable via init
    config2 = Config(profile="test")
    assert config2.model == "claude-opus-4-6"
