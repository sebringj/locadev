"""Adapters that exercise locadev core services from the host."""

from __future__ import annotations

import socket
import uuid
from typing import Any

import httpx
import redis
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from config import (
    AZURITE_CONN,
    BLOB_CONTAINER,
    BRIDGE,
    CHAT_DEPLOYMENT,
    EMBED_DEPLOYMENT,
    PGLITE,
    REDIS_URL,
    SB_QUEUE,
    SERVICEBUS_CONN,
    TOPAZ,
)


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def health_board() -> list[dict[str, Any]]:
    checks = [
        ("Azurite blob", 10000, None),
        ("Service Bus AMQP", 5672, None),
        ("Service Bus HTTP", 5300, f"http://127.0.0.1:5300/health"),
        ("Bridge", 8090, f"{BRIDGE}/health"),
        ("PGlite", 5433, f"{PGLITE}/health"),
        ("Topaz", 8484, None),
        ("Redis", 6380, None),
    ]
    out = []
    for name, port, url in checks:
        open_ = port_open(port)
        detail = ""
        if open_ and url:
            try:
                r = httpx.get(url, timeout=2.0)
                detail = r.text[:200]
            except Exception as e:
                detail = f"http error: {e}"
                open_ = False
        out.append({"name": name, "port": port, "ok": open_, "detail": detail})
    return out


def topaz_require(user: str, action: str, path: str = "access") -> dict[str, Any]:
    try:
        r = httpx.post(
            f"{TOPAZ}/api/v2/authz/is",
            json={
                "identity_context": {"type": "IDENTITY_TYPE_NONE", "identity": ""},
                "policy_context": {"path": path, "decisions": ["allowed"]},
                "resource_context": {"user": user, "action": action},
            },
            timeout=5.0,
        )
        r.raise_for_status()
        allowed = bool(r.json()["decisions"][0]["is"])
        return {"allowed": allowed, "user": user, "action": action, "error": None}
    except Exception as e:
        return {
            "allowed": False,
            "user": user,
            "action": action,
            "error": f"fail-closed: {e}",
        }


def blob_list() -> list[str]:
    client = BlobServiceClient.from_connection_string(AZURITE_CONN)
    c = client.get_container_client(BLOB_CONTAINER)
    try:
        c.create_container()
    except Exception:
        pass
    return [b.name for b in c.list_blobs()]


def blob_upload(name: str, data: bytes) -> str:
    client = BlobServiceClient.from_connection_string(AZURITE_CONN)
    c = client.get_container_client(BLOB_CONTAINER)
    try:
        c.create_container()
    except Exception:
        pass
    c.upload_blob(name, data, overwrite=True)
    return name


def blob_download(name: str) -> bytes:
    client = BlobServiceClient.from_connection_string(AZURITE_CONN)
    return (
        client.get_container_client(BLOB_CONTAINER).download_blob(name).readall()
    )


def sb_send(body: str) -> str:
    with ServiceBusClient.from_connection_string(SERVICEBUS_CONN) as client:
        with client.get_queue_sender(SB_QUEUE) as sender:
            sender.send_messages(ServiceBusMessage(body))
    return body


def sb_receive() -> str | None:
    with ServiceBusClient.from_connection_string(SERVICEBUS_CONN) as client:
        with client.get_queue_receiver(SB_QUEUE, max_wait_time=5) as receiver:
            msgs = receiver.receive_messages(max_message_count=1, max_wait_time=5)
            if not msgs:
                return None
            msg = msgs[0]
            text = str(msg)
            try:
                body = b"".join(msg.body) if msg.body else b""
                if body:
                    text = body.decode("utf-8", errors="replace")
            except Exception:
                pass
            receiver.complete_message(msg)
            return text


def bridge_chat(prompt: str) -> str:
    client = AzureOpenAI(
        azure_endpoint=BRIDGE,
        api_key="not-used",
        api_version="2025-01-01-preview",
    )
    resp = client.chat.completions.create(
        model=CHAT_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def bridge_embed(text: str) -> dict[str, Any]:
    client = AzureOpenAI(
        azure_endpoint=BRIDGE,
        api_key="not-used",
        api_version="2025-01-01-preview",
    )
    resp = client.embeddings.create(model=EMBED_DEPLOYMENT, input=text)
    emb = resp.data[0].embedding
    return {"dim": len(emb), "preview": emb[:6]}


def pglite_notes() -> list[dict[str, Any]]:
    r = httpx.post(
        f"{PGLITE}/sql",
        json={"sql": "select id, body from notes order by id limit 50", "params": []},
        timeout=10.0,
    )
    r.raise_for_status()
    return r.json().get("rows") or []


def pglite_add_note(body: str) -> str:
    nid = str(uuid.uuid4())
    r = httpx.post(
        f"{PGLITE}/sql",
        json={
            "sql": "insert into notes (id, body) values ($1, $2)",
            "params": [nid, body],
        },
        timeout=10.0,
    )
    r.raise_for_status()
    if r.json().get("error"):
        raise RuntimeError(r.json()["error"])
    return nid


def redis_ping_set_get(key: str, value: str) -> dict[str, Any]:
    r = redis.from_url(REDIS_URL)
    r.set(key, value)
    got = r.get(key)
    if isinstance(got, bytes):
        got = got.decode()
    return {"key": key, "set": value, "got": got, "ping": r.ping()}
