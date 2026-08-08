#!/usr/bin/env python3
"""E2E proof: real AzureOpenAI client against the locadev bridge."""

from __future__ import annotations

import os
import sys

from openai import AzureOpenAI


def main() -> int:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "http://127.0.0.1:8090")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", "not-used"),
        api_version="2025-01-01-preview",
    )

    chat = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "ping from harness"}],
    )
    content = chat.choices[0].message.content or ""
    print("chat:", content[:200])

    emb = client.embeddings.create(
        model="text-embedding-ada-002",
        input="locadev harness embedding",
    )
    dim = len(emb.data[0].embedding)
    print("embedding dim:", dim)
    if dim != int(os.environ.get("EMBED_DIM", "1536")):
        print(f"FAIL: expected embed dim 1536, got {dim}", file=sys.stderr)
        return 1
    if not content:
        print("FAIL: empty chat content", file=sys.stderr)
        return 1
    print("harness OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
