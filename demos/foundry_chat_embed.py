#!/usr/bin/env python3
"""Azure OpenAI chat + embeddings via bridge; both require Topaz infer."""

from __future__ import annotations

import sys

from openai import AzureOpenAI

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require


def main() -> int:
    require("alice@example.com", "infer")
    client = AzureOpenAI(
        azure_endpoint="http://127.0.0.1:8090",
        api_key="not-used",
        api_version="2025-01-01-preview",
    )
    chat = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "demo infer"}],
    )
    assert chat.choices[0].message.content
    emb = client.embeddings.create(model="text-embedding-ada-002", input="demo")
    assert len(emb.data[0].embedding) == 1536
    require("bob@example.com", "infer")  # viewer can infer
    try:
        require("bob@example.com", "write")
        print("FAIL unexpected")
        return 1
    except PermissionError:
        print("OK: alice+bob infer, embeddings 1536")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
