"""Fake Slack for local testing — no workspace, no OAuth.

Enough parity to:
  - post messages (Web API shape)
  - list/read history
  - inject user messages (bot/event tests)
  - **see everything** via /messages JSON and /ui HTML

Auth: any Bearer/xoxb token accepted (ignored). api-version N/A.
Out of scope: real RTM/Socket Mode, OAuth, files, reactions beyond stubs.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import FastAPI, Form, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="locadev-fake-slack")

# channel_id -> meta
_channels: dict[str, dict[str, Any]] = {
    "C_GENERAL": {
        "id": "C_GENERAL",
        "name": "general",
        "is_channel": True,
        "is_private": False,
    },
    "C_DEV": {
        "id": "C_DEV",
        "name": "dev",
        "is_channel": True,
        "is_private": False,
    },
    "D_ALICE": {
        "id": "D_ALICE",
        "name": "dm-alice",
        "is_im": True,
        "user": "U_ALICE",
    },
}

# all messages newest last (append order)
_messages: list[dict[str, Any]] = []
_seq = 0.0


def _ts() -> str:
    global _seq
    _seq += 1
    # Slack-like ts: seconds.micro as string; keep monotonic via counter fraction
    return f"{int(time.time())}.{int(_seq):06d}"


def _ok(**extra: Any) -> dict[str, Any]:
    return {"ok": True, **extra}


def _err(msg: str) -> dict[str, Any]:
    return {"ok": False, "error": msg}


def _auth_ok(authorization: str | None) -> bool:
    # Accept missing or any token for local dev
    return True


def _store_message(
    *,
    channel: str,
    text: str,
    user: str = "U_BOT",
    username: str | None = None,
    thread_ts: str | None = None,
    direction: str = "bot",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if channel not in _channels:
        _channels[channel] = {
            "id": channel,
            "name": channel.lower(),
            "is_channel": True,
        }
    ts = _ts()
    msg: dict[str, Any] = {
        "type": "message",
        "ts": ts,
        "channel": channel,
        "user": user,
        "text": text,
        "username": username or user,
        "direction": direction,
        "received_at": len(_messages) + 1,  # monotonic for tests
    }
    if thread_ts:
        msg["thread_ts"] = thread_ts
    if extra:
        msg.update(extra)
    _messages.append(msg)
    return msg


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "fake-slack",
        "messages": len(_messages),
        "channels": list(_channels.keys()),
    }


# --- Slack Web API shapes (form or JSON) ---


async def _body_dict(request: Request) -> dict[str, Any]:
    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        try:
            return await request.json()
        except Exception:
            return {}
    form = await request.form()
    return {k: form.get(k) for k in form.keys()}


@app.api_route("/api/auth.test", methods=["GET", "POST"])
async def auth_test(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _ = await _body_dict(request)
    if not _auth_ok(authorization):
        return _err("invalid_auth")
    return _ok(
        url="https://locadev.slack.local/",
        team="locadev",
        user="bot",
        team_id="T_LOCADEV",
        user_id="U_BOT",
        bot_id="B_LOCADEV",
    )


@app.api_route("/api/chat.postMessage", methods=["POST"])
async def chat_post_message(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await _body_dict(request)
    channel = str(body.get("channel") or "")
    text = str(body.get("text") or "")
    if not channel:
        return _err("channel_not_found")
    thread_ts = body.get("thread_ts")
    msg = _store_message(
        channel=channel,
        text=text,
        user=str(body.get("user") or "U_BOT"),
        username=str(body.get("username") or "locadev-bot"),
        thread_ts=str(thread_ts) if thread_ts else None,
        direction="bot",
    )
    return _ok(channel=channel, ts=msg["ts"], message=msg)


@app.api_route("/api/chat.update", methods=["POST"])
async def chat_update(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await _body_dict(request)
    channel = str(body.get("channel") or "")
    ts = str(body.get("ts") or "")
    text = str(body.get("text") or "")
    for m in _messages:
        if m.get("channel") == channel and m.get("ts") == ts:
            m["text"] = text
            m["edited"] = {"ts": _ts()}
            return _ok(channel=channel, ts=ts, text=text)
    return _err("message_not_found")


@app.api_route("/api/conversations.history", methods=["GET", "POST"])
async def conversations_history(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await _body_dict(request)
    # also query params
    q = request.query_params
    channel = str(body.get("channel") or q.get("channel") or "")
    limit = int(body.get("limit") or q.get("limit") or 100)
    if not channel:
        return _err("channel_not_found")
    msgs = [m for m in _messages if m.get("channel") == channel]
    # Slack returns newest first typically for history pages — use reverse chrono
    msgs = list(reversed(msgs[-limit:]))
    # strip internal fields for API shape
    public = []
    for m in msgs:
        public.append(
            {
                k: v
                for k, v in m.items()
                if k not in ("direction", "received_at")
            }
        )
    return _ok(messages=public, has_more=False)


@app.api_route("/api/conversations.list", methods=["GET", "POST"])
async def conversations_list(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _ = await _body_dict(request)
    return _ok(channels=list(_channels.values()))


@app.api_route("/api/chat.delete", methods=["POST"])
async def chat_delete(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    body = await _body_dict(request)
    channel = str(body.get("channel") or "")
    ts = str(body.get("ts") or "")
    before = len(_messages)
    _messages[:] = [
        m
        for m in _messages
        if not (m.get("channel") == channel and m.get("ts") == ts)
    ]
    if len(_messages) == before:
        return _err("message_not_found")
    return _ok(channel=channel, ts=ts)


# --- Test hooks (not real Slack; like fake-teams inject) ---


@app.post("/api/inject")
async def inject(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Simulate a user/human message into a channel."""
    body = body or {}
    channel = str(body.get("channel") or "C_GENERAL")
    text = str(body.get("text") or body.get("message") or "")
    user = str(body.get("user") or "U_ALICE")
    username = str(body.get("username") or "alice")
    msg = _store_message(
        channel=channel,
        text=text,
        user=user,
        username=username,
        thread_ts=str(body["thread_ts"]) if body.get("thread_ts") else None,
        direction="user",
    )
    return _ok(message=msg)


@app.get("/messages")
def get_messages(
    channel: str | None = None,
    direction: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Admin/test: see all captured messages (with direction)."""
    items = _messages
    if channel:
        items = [m for m in items if m.get("channel") == channel]
    if direction:
        items = [m for m in items if m.get("direction") == direction]
    items = items[-limit:]
    return {
        "messages": items,
        "count": len(items),
        "channels": list(_channels.keys()),
    }


@app.delete("/messages")
def clear_messages() -> dict[str, Any]:
    n = len(_messages)
    _messages.clear()
    return {"cleared": n}


@app.post("/api/reset")
def reset() -> dict[str, str]:
    _messages.clear()
    return {"status": "reset"}


@app.get("/ui", response_class=HTMLResponse)
def ui() -> str:
    """Simple message viewer for humans (parity: *see* messages)."""
    rows = []
    for m in reversed(_messages[-100:]):
        direction = m.get("direction") or "?"
        badge = "bot" if direction == "bot" else "user"
        color = "#3b82f6" if direction == "bot" else "#22c55e"
        rows.append(
            f"<tr>"
            f"<td style='color:{color};font-weight:600'>{badge}</td>"
            f"<td class='mono'>{m.get('channel')}</td>"
            f"<td class='mono'>{m.get('username') or m.get('user')}</td>"
            f"<td>{_html(m.get('text') or '')}</td>"
            f"<td class='mono'>{m.get('ts')}</td>"
            f"</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='5'>No messages yet. POST /api/chat.postMessage or /api/inject</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>fake-slack · locadev</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 1.5rem; }}
    h1 {{ font-size: 1.25rem; }}
    a {{ color: #93c5fd; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #1e293b; vertical-align: top; }}
    th {{ color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; }}
    .mono {{ font-family: ui-monospace, monospace; font-size: 0.8rem; color: #94a3b8; }}
    .meta {{ color: #64748b; font-size: 0.85rem; }}
    code {{ background: #1e293b; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>locadev · fake Slack</h1>
  <p class="meta">
    Messages: {len(_messages)} ·
    <a href="/messages">JSON /messages</a> ·
    <a href="/health">/health</a> ·
    <a href="/ui">refresh</a>
  </p>
  <p class="meta">
    Post: <code>POST /api/chat.postMessage</code> ·
    History: <code>POST /api/conversations.history</code> ·
    Inject user: <code>POST /api/inject</code>
  </p>
  <table>
    <thead><tr><th>dir</th><th>channel</th><th>from</th><th>text</th><th>ts</th></tr></thead>
    <tbody>
      {body}
    </tbody>
  </table>
</body>
</html>"""


def _html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "locadev-fake-slack",
        "ui": "/ui",
        "messages": "/messages",
        "health": "/health",
        "web_api": [
            "/api/auth.test",
            "/api/chat.postMessage",
            "/api/chat.update",
            "/api/chat.delete",
            "/api/conversations.history",
            "/api/conversations.list",
            "/api/inject",
        ],
    }
