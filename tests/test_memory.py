"""Tests for memory system."""

from datetime import date, timedelta

from agentkit.memory import Memory


def test_read_long_term_empty(tmp_path):
    mem = Memory(tmp_path / "memory")
    assert mem.read_long_term() == ""


def test_write_and_read_long_term(tmp_path):
    mem = Memory(tmp_path / "memory")
    mem.write_long_term("fact one")
    assert mem.read_long_term() == "fact one"


def test_append_long_term(tmp_path):
    mem = Memory(tmp_path / "memory")
    mem.append_long_term("first")
    mem.append_long_term("second")
    content = mem.read_long_term()
    assert "first" in content
    assert "second" in content


def test_read_today_empty(tmp_path):
    mem = Memory(tmp_path / "memory")
    assert mem.read_today() == ""


def test_append_today_creates_file_with_header(tmp_path):
    mem = Memory(tmp_path / "memory")
    mem.append_today("observation one")
    content = mem.read_today()
    assert date.today().isoformat() in content
    assert "observation one" in content


def test_append_today_appends(tmp_path):
    mem = Memory(tmp_path / "memory")
    mem.append_today("first")
    mem.append_today("second")
    content = mem.read_today()
    assert "first" in content
    assert "second" in content


def test_read_recent_days(tmp_path):
    mem = Memory(tmp_path / "memory")
    # Write files for today and yesterday
    today = date.today()
    yesterday = today - timedelta(days=1)
    (tmp_path / "memory" / "daily" / f"{today.isoformat()}.md").write_text("today entry")
    (tmp_path / "memory" / "daily" / f"{yesterday.isoformat()}.md").write_text("yesterday entry")
    recent = mem.read_recent(days=3)
    assert "today entry" in recent
    assert "yesterday entry" in recent
