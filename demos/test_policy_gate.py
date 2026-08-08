"""Gate 5: alice allowed / bob denied on write."""

from __future__ import annotations

import pytest

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require


def test_alice_write_bob_denied():
    require("alice@example.com", "write")
    with pytest.raises(PermissionError):
        require("bob@example.com", "write")
    require("bob@example.com", "read")
