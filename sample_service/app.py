"""Minimal FastAPI sample consumer wired to locadev services by Docker DNS."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI
from openai import AzureOpenAI

app = FastAPI(title="locadev-sample")

PGLITE_URL = os.environ.get("PGLITE_URL", "http://pglite:5433").rstrip("/")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
AZURE_OPENAI_ENDPOINT = os.environ.get(
    "AZURE_OPENAI_ENDPOINT", "http://bridge:8090/"
)
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "not-used")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1"
)
AZURE_OPENAI_API_VERSION = os.environ.get(
    "AZURE_OPENAI_API_VERSION", "2025-01-01-preview"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo/note")
async def demo_note() -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"{PGLITE_URL}/sql",
            json={"sql": "select id, body from notes limit 5", "params": []},
        )
        r.raise_for_status()
        return r.json()


@app.get("/demo/chat")
def demo_chat(q: str = "hello from sample_service") -> Any:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    resp = client.chat.completions.create(
        model=AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[{"role": "user", "content": q}],
    )
    return {"reply": resp.choices[0].message.content}


@app.get("/demo/redis")
def demo_redis() -> Any:
    import redis

    r = redis.from_url(REDIS_URL)
    r.set("locadev:sample", "ok")
    return {"value": r.get("locadev:sample")}
