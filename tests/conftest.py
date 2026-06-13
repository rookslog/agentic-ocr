"""Shared pytest fixtures for the checker-suite tests.

Loads the committed PageGT-shaped fixtures (synthetic, scriptorium-derived /
public-domain text — data-hygiene compliant) as plain dicts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def minimal_gt() -> dict[str, Any]:
    """The scriptorium minimal_page fixture (canonical end-to-end smoke GT)."""
    return _load("minimal_page.gt.json")


@pytest.fixture
def minimal_candidate() -> dict[str, Any]:
    """A faithful candidate for the minimal page (whitespace varies; passes)."""
    return _load("minimal_page.candidate.json")


@pytest.fixture
def apparatus_gt() -> dict[str, Any]:
    """A richer apparatus page: heading + two body blocks + an anchored note."""
    return _load("apparatus_page.gt.json")


@pytest.fixture
def apparatus_candidate() -> dict[str, Any]:
    """A faithful candidate for the apparatus page (passes all checkers)."""
    return _load("apparatus_page.candidate.json")
