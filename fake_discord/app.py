"""Fake Discord for local testing — no guild, no OAuth, no Gateway.

Enough parity to:
  - create/list channel messages (REST v10 shape)
  - inject user messages
  - **see everything** via /messages JSON and /ui HTML

Auth: any Authorization: Bot … / Bearer … accepted (ignored).
Out of scope: real Gateway/websocket, slash commands beyond stubs, files, reactions.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="locadev-fake-discord")

GUILD_ID = "g_locadev"

_channels: dict[str, dict[str, Any]] = {
    "c_general": {
        "id": "c_general",
        "type": 0,  # GUILD_TEXT
        "guild_id": GUILD_ID,
        "name": "general",
        "position": 0,
    },
    "c_dev": {
        "id": "c_dev",
        "type": 0,
        "guild_id": GUILD_ID,
        "name": "dev",
        "position": 1,
    },
    "c_dm_alice": {
        "id": "c_dm_alice",
        "type": 1,  # DM
        "name": "dm-alice",
        "recipients": [{"id": "u_alice", "username": "alice"}],
    },
}

_messages: list[dict[str, Any]] = []
_snow = 1000000000000000000


def _snowflake() -> str:
    global _snow
    _snow += 1
    return str(_snow)


def _iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000000+00:00", time.gmtime())


def _ensure_channel(channel_id: str) -> None:
    if channel_id not in _channels:
        _channels[channel_id] = {
            "id": channel_id,
            "type": 0,
            "guild_id": GUILD_ID,
            "name": channel_id,
            "position": len(_channels),
        }


def _store_message(
    *,
    channel_id: str,
    content: str,
    author_id: str = "u_bot",
    username: str = "locadev-bot",
    bot: bool = True,
    direction: str = "bot",
    message_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_channel(channel_id)
    mid = _snowflake()
    msg: dict[str, Any] = {
        "id": mid,
        "type": 0,
        "channel_id": channel_id,
        "content": content,
        "timestamp": _iso(),
        "edited_timestamp": None,
        "tts": False,
        "mention_everyone": False,
        "mentions": [],
        "mention_roles": [],
        "attachments": [],
        "embeds": [],
        "pinned": False,
        "author": {
            "id": author_id,
            "username": username,
            "discriminator": "0000",
            "bot": bot,
            "avatar": None,
        },
        # locadev admin fields
        "direction": direction,
        "received_at": len(_messages) + 1,
    }
    if message_reference:
        msg["message_reference"] = message_reference
    _messages.append(msg)
    return msg


def _public_message(m: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in m.items() if k not in ("direction", "received_at")}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "fake-discord",
        "messages": len(_messages),
        "channels": list(_channels.keys()),
        "guild_id": GUILD_ID,
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "locadev-fake-discord",
        "ui": "/ui",
        "messages": "/messages",
        "health": "/health",
        "rest": [
            "GET/POST /api/v10/channels/{id}/messages",
            "GET /api/v10/guilds/{id}/channels",
            "GET /api/v10/users/@me",
            "POST /api/inject",
        ],
    }


# --- Discord REST-ish ---


@app.get("/api/v10/users/@me")
@app.get("/api/v9/users/@me")
def users_me(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    return {
        "id": "u_bot",
        "username": "locadev-bot",
        "discriminator": "0000",
        "bot": True,
        "verified": True,
    }


@app.get("/api/v10/guilds/{guild_id}/channels")
@app.get("/api/v9/guilds/{guild_id}/channels")
def guild_channels(guild_id: str) -> list[dict[str, Any]]:
    return [
        c
        for c in _channels.values()
        if c.get("guild_id") == guild_id or c.get("type") == 0
    ]


@app.get("/api/v10/channels/{channel_id}/messages")
@app.get("/api/v9/channels/{channel_id}/messages")
def get_channel_messages(
    channel_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    _ensure_channel(channel_id)
    msgs = [m for m in _messages if m.get("channel_id") == channel_id]
    # Discord returns newest first
    msgs = list(reversed(msgs[-limit:]))
    return [_public_message(m) for m in msgs]


@app.post("/api/v10/channels/{channel_id}/messages")
@app.post("/api/v9/channels/{channel_id}/messages")
async def create_message(
    channel_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    content = str(body.get("content") or "")
    ref = body.get("message_reference")
    msg = _store_message(
        channel_id=channel_id,
        content=content,
        author_id=str(body.get("author_id") or "u_bot"),
        username=str(body.get("username") or "locadev-bot"),
        bot=True,
        direction="bot",
        message_reference=ref if isinstance(ref, dict) else None,
    )
    return _public_message(msg)


@app.delete(
    "/api/v10/channels/{channel_id}/messages/{message_id}",
    response_model=None,
)
@app.delete(
    "/api/v9/channels/{channel_id}/messages/{message_id}",
    response_model=None,
)
def delete_message(channel_id: str, message_id: str) -> JSONResponse:
    before = len(_messages)
    _messages[:] = [
        m
        for m in _messages
        if not (m.get("channel_id") == channel_id and m.get("id") == message_id)
    ]
    if len(_messages) == before:
        return JSONResponse(status_code=404, content={"message": "Unknown Message"})
    return JSONResponse(status_code=204, content=None)


@app.patch(
    "/api/v10/channels/{channel_id}/messages/{message_id}",
    response_model=None,
)
@app.patch(
    "/api/v9/channels/{channel_id}/messages/{message_id}",
    response_model=None,
)
async def edit_message(
    channel_id: str, message_id: str, request: Request
) -> Any:
    try:
        body = await request.json()
    except Exception:
        body = {}
    for m in _messages:
        if m.get("channel_id") == channel_id and m.get("id") == message_id:
            if "content" in body:
                m["content"] = str(body["content"])
            m["edited_timestamp"] = _iso()
            return _public_message(m)
    return JSONResponse(status_code=404, content={"message": "Unknown Message"})


# --- Test hooks ---


@app.post("/api/inject")
async def inject(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Simulate a human/user message (not a real Discord Gateway event)."""
    body = body or {}
    channel_id = str(body.get("channel_id") or body.get("channel") or "c_general")
    content = str(body.get("content") or body.get("text") or body.get("message") or "")
    msg = _store_message(
        channel_id=channel_id,
        content=content,
        author_id=str(body.get("user_id") or body.get("user") or "u_alice"),
        username=str(body.get("username") or "alice"),
        bot=False,
        direction="user",
    )
    return {"ok": True, "message": msg}


@app.get("/messages")
def admin_messages(
    channel_id: str | None = None,
    direction: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    items = _messages
    if channel_id:
        items = [m for m in items if m.get("channel_id") == channel_id]
    if direction:
        items = [m for m in items if m.get("direction") == direction]
    items = items[-limit:]
    return {
        "messages": items,
        "count": len(items),
        "channels": list(_channels.keys()),
    }


@app.delete("/messages")
def clear_messages() -> dict[str, int]:
    n = len(_messages)
    _messages.clear()
    return {"cleared": n}


@app.post("/api/reset")
def reset() -> dict[str, str]:
    _messages.clear()
    return {"status": "reset"}


def _html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
    rows = []
    for m in reversed(_messages[-100:]):
        direction = m.get("direction") or "?"
        badge = "bot" if direction == "bot" else "user"
        color = "#5865F2" if direction == "bot" else "#57F287"
        author = (m.get("author") or {}).get("username") or "?"
        rows.append(
            f"<tr>"
            f"<td style='color:{color};font-weight:600'>{badge}</td>"
            f"<td class='mono'>{_html(str(m.get('channel_id')))}</td>"
            f"<td>{_html(str(author))}</td>"
            f"<td>{_html(str(m.get('content') or ''))}</td>"
            f"<td class='mono'>{_html(str(m.get('id')))}</td>"
            f"</tr>"
        )
    body = (
        "\n".join(rows)
        or "<tr><td colspan='5'>No messages yet. POST /api/v10/channels/{{id}}/messages or /api/inject</td></tr>"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>fake-discord · locadev</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #1e1f22; color: #dbdee1; margin: 0; padding: 1.5rem; }}
    h1 {{ font-size: 1.25rem; color: #fff; }}
    a {{ color: #00a8fc; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #2b2d31; vertical-align: top; }}
    th {{ color: #949ba4; font-size: 0.75rem; text-transform: uppercase; }}
    .mono {{ font-family: ui-monospace, monospace; font-size: 0.8rem; color: #949ba4; }}
    .meta {{ color: #949ba4; font-size: 0.85rem; }}
    code {{ background: #2b2d31; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>locadev · fake Discord</h1>
  <p class="meta">
    Messages: {len(_messages)} ·
    <a href="/messages">JSON /messages</a> ·
    <a href="/health">/health</a> ·
    <a href="/ui">refresh</a>
  </p>
  <p class="meta">
    Create: <code>POST /api/v10/channels/c_general/messages</code> ·
    List: <code>GET /api/v10/channels/c_general/messages</code> ·
    Inject user: <code>POST /api/inject</code>
  </p>
  <table>
    <thead><tr><th>dir</th><th>channel</th><th>from</th><th>content</th><th>id</th></tr></thead>
    <tbody>
      {body}
    </tbody>
  </table>
</body>
</html>"""
