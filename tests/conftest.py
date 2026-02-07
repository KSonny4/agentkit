"""Shared test fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with standard directory structure."""
    (tmp_path / "profiles" / "test").mkdir(parents=True)
    (tmp_path / "memory" / "daily").mkdir(parents=True)
    (tmp_path / "data").mkdir()
    return tmp_path
