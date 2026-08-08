#!/usr/bin/env python3
"""S3 list/get against MiniStack seed keys; read=crawl. Skips if aws profile off."""

from __future__ import annotations

import socket
import sys

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require


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
    if not port_open(4566):
        print("SKIP: ministack not up")
        return 0
    import boto3

    require("alice@example.com", "crawl")
    s3 = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )
    buckets = s3.list_buckets()
    assert "Buckets" in buckets
    require("bob@example.com", "crawl")
    print("OK: crawl list buckets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
