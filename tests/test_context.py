"""Tests for context builder."""

from agentkit.config import Config
from agentkit.context import ContextBuilder
from agentkit.memory import Memory


def test_build_context_includes_identity(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "profiles" / "test" / "identity.md").write_text("I am a test agent.")
    config = Config(profile="test", project_root=tmp_path)
    memory = Memory(tmp_path / "memory")
    ctx = ContextBuilder(config, memory)
    prompt = ctx.build_system_prompt()
    assert "I am a test agent." in prompt


def test_build_context_includes_memory(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    config = Config(profile="test", project_root=tmp_path)
    memory = Memory(tmp_path / "memory")
    memory.write_long_term("important fact")
    ctx = ContextBuilder(config, memory)
    prompt = ctx.build_system_prompt()
    assert "important fact" in prompt


def test_build_context_includes_tools(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "profiles" / "test" / "tools.md").write_text("- shell: run commands")
    config = Config(profile="test", project_root=tmp_path)
    memory = Memory(tmp_path / "memory")
    ctx = ContextBuilder(config, memory)
    prompt = ctx.build_system_prompt()
    assert "shell: run commands" in prompt


def test_build_context_includes_orientation(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    config = Config(profile="test", project_root=tmp_path)
    memory = Memory(tmp_path / "memory")
    memory.append_today("worked on feature X")
    ctx = ContextBuilder(config, memory)
    prompt = ctx.build_system_prompt()
    assert "worked on feature X" in prompt
    assert "Orientation" in prompt


def test_build_task_prompt(tmp_path):
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    config = Config(profile="test", project_root=tmp_path)
    memory = Memory(tmp_path / "memory")
    ctx = ContextBuilder(config, memory)
    prompt = ctx.build_task_prompt("analyze this data")
    assert "analyze this data" in prompt
    assert "MEMORY:" in prompt
    assert "Do NOT ask for confirmation" in prompt
