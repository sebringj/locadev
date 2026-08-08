#!/usr/bin/env python3
"""App SQL via PGlite HTTP + optional vector insert, Topaz-gated."""

from __future__ import annotations

import sys
import uuid

import httpx

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require

PGLITE = "http://127.0.0.1:5433"


def write_note(user: str, body: str) -> str:
    require(user, "write")
    nid = str(uuid.uuid4())
    with httpx.Client(timeout=10.0) as c:
        r = c.post(
            f"{PGLITE}/sql",
            json={
                "sql": "insert into notes (id, body) values ($1, $2)",
                "params": [nid, body],
            },
        )
        r.raise_for_status()
    return nid


def read_notes(user: str) -> list:
    require(user, "read")
    with httpx.Client(timeout=10.0) as c:
        r = c.post(
            f"{PGLITE}/sql",
            json={"sql": "select id, body from notes order by id limit 20", "params": []},
        )
        r.raise_for_status()
        return r.json()["rows"]


def main() -> int:
    write_note("alice@example.com", "alice note")
    rows = read_notes("bob@example.com")
    assert rows
    try:
        write_note("bob@example.com", "bob cannot")
        print("FAIL: bob write should be denied")
        return 1
    except PermissionError:
        print("OK: alice write, bob read, bob write denied")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
