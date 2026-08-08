#!/usr/bin/env python3
"""Cosmos chat-history style write/read, Topaz-gated. Skips if cosmos down."""

from __future__ import annotations

import socket
import sys
import uuid

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require

ENDPOINT = "http://127.0.0.1:8081"
KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)


def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main() -> int:
    if not port_open(8081):
        print("SKIP: cosmos not up")
        return 0
    from azure.cosmos import CosmosClient, PartitionKey

    require("alice@example.com", "write")
    client = CosmosClient(ENDPOINT, credential=KEY, connection_verify=False)
    db = client.create_database_if_not_exists("locadev")
    container = db.create_container_if_not_exists(
        "chats", partition_key=PartitionKey(path="/userId")
    )
    doc_id = str(uuid.uuid4())
    container.upsert_item(
        {"id": doc_id, "userId": "alice", "content": "hello cosmos"}
    )
    require("bob@example.com", "read")
    got = container.read_item(doc_id, partition_key="alice")
    assert got["content"] == "hello cosmos"
    try:
        require("bob@example.com", "write")
        print("FAIL: bob write should be denied")
        return 1
    except PermissionError:
        print("OK: alice write, bob read, bob write denied")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
