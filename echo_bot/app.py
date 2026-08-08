"""Echo bot written like a TeamsActivityHandler — exercises fake-teams control plane.

ECHO_BOT_BRAIN empty => plain echo (required for tests/teams).
Default brain is the sandbox bridge.
HITL approve/reject invokes are Topaz-gated (approval policy).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="locadev-echo-bot")

# Empty string selects plain echo. Unset defaults to bridge.
_brain_raw = os.environ.get("ECHO_BOT_BRAIN", "http://bridge:8090")
BRIDGE_ENDPOINT = (_brain_raw or "").rstrip("/")
TOPAZ_ENDPOINT = os.environ.get("TOPAZ_ENDPOINT", "http://topaz:8383").rstrip("/")
USE_ECHO = not BRIDGE_ENDPOINT


async def topaz_allowed(user: str, action: str, path: str = "approval") -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{TOPAZ_ENDPOINT}/api/v2/authz/is",
                json={
                    "identity_context": {
                        "type": "IDENTITY_TYPE_NONE",
                        "identity": "",
                    },
                    "policy_context": {"path": path, "decisions": ["allowed"]},
                    "resource_context": {"user": user, "action": action},
                },
            )
            r.raise_for_status()
            data = r.json()
            return bool(data["decisions"][0]["is"])
    except Exception:
        return False  # fail closed


async def brain_reply(text: str) -> str:
    if USE_ECHO:
        return f"echo: {text}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{BRIDGE_ENDPOINT}/openai/deployments/gpt-4.1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": text}],
                    "stream": False,
                },
                headers={"api-key": "not-used"},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"echo (bridge_error): {text} [{type(e).__name__}]"


async def reply_to_conversation(activity: dict[str, Any], text: str) -> None:
    service_url = (activity.get("serviceUrl") or "").rstrip("/")
    conv = (activity.get("conversation") or {}).get("id")
    if not service_url or not conv:
        return
    payload = {
        "type": "message",
        "text": text,
        "from": activity.get("recipient"),
        "recipient": activity.get("from"),
        "conversation": activity.get("conversation"),
        "channelId": "msteams",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{service_url}/v3/conversations/{conv}/activities",
                json=payload,
            )
    except Exception:
        pass


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "brain": "echo" if USE_ECHO else BRIDGE_ENDPOINT,
        "topaz": TOPAZ_ENDPOINT,
    }


@app.post("/api/messages")
async def messages(request: Request) -> Any:
    activity = await request.json()
    atype = activity.get("type") or ""

    if atype == "conversationUpdate":
        bot_id = (activity.get("recipient") or {}).get("id")
        for m in activity.get("membersAdded") or []:
            if m.get("id") == bot_id:
                continue  # never welcome the bot itself
            await reply_to_conversation(
                activity, f"Welcome {m.get('name') or m.get('id')}!"
            )
        return {}

    if atype == "message":
        text = activity.get("text") or ""
        reply = await brain_reply(text)
        await reply_to_conversation(activity, reply)
        return {}

    if atype == "messageReaction":
        await reply_to_conversation(activity, "reaction acknowledged")
        return {}

    if atype == "invoke":
        value = activity.get("value") or {}
        verb = value.get("verb") or ""
        user = (
            value.get("user")
            or (activity.get("from") or {}).get("name")
            or (activity.get("from") or {}).get("id")
            or ""
        )
        if verb in ("approve", "reject"):
            allowed = await topaz_allowed(str(user), verb, path="approval")
            if not allowed:
                await reply_to_conversation(activity, f"refused: {verb} denied for {user}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": 403,
                        "body": {"error": "forbidden", "verb": verb, "user": user},
                    },
                )
            await reply_to_conversation(activity, f"confirmed: {verb} by {user}")
            return {"status": 200, "body": {"ok": True, "verb": verb}}

        # Adaptive Card / generic invoke
        return {
            "status": 200,
            "body": {"type": "application/vnd.microsoft.card.adaptive", "value": value},
        }

    # ack everything else
    return {}
