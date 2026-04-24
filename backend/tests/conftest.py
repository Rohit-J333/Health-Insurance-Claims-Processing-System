"""Shared test fixtures."""

import sys
from pathlib import Path

import pytest

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.policy_loader import PolicyLoader
from app.services.trace_logger import TraceLogger


@pytest.fixture
def policy():
    return PolicyLoader()


@pytest.fixture
def trace():
    return TraceLogger("TEST-CLAIM")
