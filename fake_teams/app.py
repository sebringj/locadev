"""Local Teams channel control plane — no M365 tenant, no tunnel.

Out of scope: JWT/auth, real AAD, SharePoint-backed rosters, message-extension UI.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="locadev-fake-teams")

BOT_ENDPOINT = __import__("os").environ.get(
    "BOT_ENDPOINT", "http://echo-bot:3978/api/messages"
)
SERVICE_URL = __import__("os").environ.get(
    "SERVICE_URL", "http://fake-teams:3979"
).rstrip("/")

_messages: list[dict[str, Any]] = []
_members: list[dict[str, Any]] = [
    {
        "id": "user-alice",
        "name": "Alice",
        "aadObjectId": "alice-aad",
    },
    {
        "id": "bot-locadev",
        "name": "Locadev Bot",
    },
]
_conversations: dict[str, dict[str, Any]] = {}
_seq = 0


def _next_id(prefix: str = "act") -> str:
    global _seq
    _seq += 1
    return f"{prefix}-{_seq}-{uuid.uuid4().hex[:8]}"


def _base_activity(
    activity_type: str,
    conversation_id: str | None = None,
    from_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cid = conversation_id or "conv-default"
    if cid not in _conversations:
        _conversations[cid] = {
            "id": cid,
            "conversationType": "personal",
            "isGroup": False,
        }
    return {
        "type": activity_type,
        "id": _next_id(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channelId": "msteams",
        "serviceUrl": SERVICE_URL + "/",
        "from": from_user
        or {"id": "user-alice", "name": "Alice", "aadObjectId": "alice-aad"},
        "recipient": {"id": "bot-locadev", "name": "Locadev Bot"},
        "conversation": {
            "id": cid,
            "conversationType": _conversations[cid]["conversationType"],
            "isGroup": _conversations[cid]["isGroup"],
        },
        "channelData": {"tenant": {"id": "locadev-tenant"}},
    }


def _store(activity: dict[str, Any], direction: str) -> dict[str, Any]:
    entry = {
        **activity,
        "direction": direction,
        "_ts": time.time(),
    }
    _messages.append(entry)
    return entry


async def _post_to_bot(activity: dict[str, Any]) -> httpx.Response:
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await client.post(BOT_ENDPOINT, json=activity)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "messages": len(_messages),
        "bot_endpoint": BOT_ENDPOINT,
    }


@app.post("/api/inject")
async def inject(body: dict[str, Any] | None = None) -> Any:
    body = body or {}
    act = _base_activity(
        "message",
        conversation_id=body.get("conversation_id"),
        from_user=body.get("from"),
    )
    act["text"] = body.get("text") or body.get("message") or ""
    _store(act, "user")
    r = await _post_to_bot(act)
    return {"activity": act, "bot_status": r.status_code, "bot_body": _safe_json(r)}


@app.post("/api/conversation-update")
async def conversation_update(body: dict[str, Any] | None = None) -> Any:
    body = body or {}
    act = _base_activity("conversationUpdate", conversation_id=body.get("conversation_id"))
    act["membersAdded"] = body.get("membersAdded") or [
        {"id": "user-alice", "name": "Alice"}
    ]
    act["membersRemoved"] = body.get("membersRemoved") or []
    _store(act, "event")
    r = await _post_to_bot(act)
    return {"activity": act, "bot_status": r.status_code, "bot_body": _safe_json(r)}


@app.post("/api/reaction")
async def reaction(body: dict[str, Any] | None = None) -> Any:
    body = body or {}
    act = _base_activity("messageReaction", conversation_id=body.get("conversation_id"))
    act["reactionsAdded"] = body.get("reactionsAdded") or [
        {"type": "like", "activityId": body.get("activityId") or "unknown"}
    ]
    act["reactionsRemoved"] = body.get("reactionsRemoved") or []
    _store(act, "event")
    r = await _post_to_bot(act)
    return {"activity": act, "bot_status": r.status_code, "bot_body": _safe_json(r)}


@app.post("/api/invoke")
async def invoke(body: dict[str, Any] | None = None) -> Any:
    """Invoke is synchronous: bot InvokeResponse is in the HTTP body."""
    body = body or {}
    act = _base_activity("invoke", conversation_id=body.get("conversation_id"))
    act["name"] = body.get("name") or "adaptiveCard/action"
    act["value"] = body.get("value") or {}
    _store(act, "user")
    r = await _post_to_bot(act)
    bot_body = _safe_json(r)
    # store invokeResponse activity
    ir = _base_activity("invokeResponse", conversation_id=act["conversation"]["id"])
    ir["value"] = bot_body
    _store(ir, "bot")
    return {
        "activity": act,
        "bot_status": r.status_code,
        "invokeResponse": bot_body,
    }


def _safe_json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except Exception:
        return r.text


# --- Connector REST (bot -> channel) ---


@app.post("/v3/conversations/{conversation_id}/activities")
async def post_activity(conversation_id: str, request: Request) -> Any:
    body = await request.json()
    body.setdefault("id", _next_id())
    body.setdefault("conversation", {"id": conversation_id})
    body.setdefault("channelId", "msteams")
    _store(body, "bot")
    return {"id": body["id"]}


@app.post("/v3/conversations/{conversation_id}/activities/{activity_id}")
@app.put("/v3/conversations/{conversation_id}/activities/{activity_id}")
async def update_activity(
    conversation_id: str, activity_id: str, request: Request
) -> Any:
    body = await request.json()
    body["id"] = activity_id
    body.setdefault("conversation", {"id": conversation_id})
    _store(body, "bot")
    return {"id": activity_id}


@app.delete("/v3/conversations/{conversation_id}/activities/{activity_id}")
async def delete_activity(conversation_id: str, activity_id: str) -> Any:
    _store(
        {
            "type": "messageDelete",
            "id": activity_id,
            "conversation": {"id": conversation_id},
        },
        "bot",
    )
    return JSONResponse(status_code=200, content={})


@app.get("/v3/conversations/{conversation_id}/members")
async def members(conversation_id: str) -> list[dict[str, Any]]:
    return list(_members)


@app.get("/v3/conversations/{conversation_id}/pagedmembers")
async def paged_members(conversation_id: str) -> dict[str, Any]:
    return {"members": list(_members), "continuationToken": None}


@app.post("/v3/conversations")
async def create_conversation(body: dict[str, Any] | None = None) -> Any:
    body = body or {}
    cid = body.get("id") or _next_id("conv")
    _conversations[cid] = {
        "id": cid,
        "conversationType": body.get("conversationType") or "personal",
        "isGroup": bool(body.get("isGroup")),
    }
    return {"id": cid}


@app.get("/api/messages")
def get_messages(
    conversation_id: str | None = None,
    direction: str | None = None,
    since: float | None = None,
) -> dict[str, Any]:
    items = _messages
    if conversation_id:
        items = [
            m
            for m in items
            if (m.get("conversation") or {}).get("id") == conversation_id
        ]
    if direction:
        items = [m for m in items if m.get("direction") == direction]
    if since is not None:
        items = [m for m in items if (m.get("_ts") or 0) > since]
    next_since = max((m.get("_ts") or 0 for m in _messages), default=0)
    return {"messages": items, "next_since": next_since}


@app.get("/api/transcript")
def transcript(conversation_id: str | None = None) -> list[dict[str, Any]]:
    items = _messages
    if conversation_id:
        items = [
            m
            for m in items
            if (m.get("conversation") or {}).get("id") == conversation_id
        ]
    return items


@app.get("/api/members")
def api_members() -> list[dict[str, Any]]:
    return list(_members)


@app.post("/api/reset")
def reset() -> dict[str, str]:
    _messages.clear()
    _conversations.clear()
    return {"status": "reset"}
