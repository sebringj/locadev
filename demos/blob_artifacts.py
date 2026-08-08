#!/usr/bin/env python3
"""Blob upload/download gated by Topaz (write=editor, read=editor+viewer)."""

from __future__ import annotations

import sys

from azure.storage.blob import BlobServiceClient

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require

CONN = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10101/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)


def write(user: str, name: str, data: bytes) -> None:
    require(user, "write")
    client = BlobServiceClient.from_connection_string(CONN)
    c = client.get_container_client("locadev-demo")
    try:
        c.create_container()
    except Exception:
        pass
    c.upload_blob(name, data, overwrite=True)


def read(user: str, name: str) -> bytes:
    require(user, "read")
    client = BlobServiceClient.from_connection_string(CONN)
    return client.get_container_client("locadev-demo").download_blob(name).readall()


def main() -> int:
    write("alice@example.com", "artifact.txt", b"secret")
    assert read("alice@example.com", "artifact.txt") == b"secret"
    assert read("bob@example.com", "artifact.txt") == b"secret"
    try:
        write("bob@example.com", "nope.txt", b"x")
        print("FAIL: bob write should be denied")
        return 1
    except PermissionError:
        print("OK: alice write/read, bob read ok, bob write denied")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
