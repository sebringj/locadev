#!/usr/bin/env python3
"""Host-run MCP server exposing fake-teams channel as tools.

Repo-local only — do not copy .mcp.json into a wider workspace config.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE = os.environ.get("FAKE_TEAMS_BASE", "http://localhost:3979").rstrip("/")
mcp = FastMCP("locadev-fake-teams")


def _post(path: str, json: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=30.0) as c:
        r = c.post(f"{BASE}{path}", json=json or {})
        r.raise_for_status()
        return r.json()


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    with httpx.Client(timeout=30.0) as c:
        r = c.get(f"{BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()


@mcp.tool()
def teams_send(text: str, conversation_id: str | None = None) -> Any:
    """Send a user message into the fake Teams channel."""
    body: dict[str, Any] = {"text": text}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return _post("/api/inject", body)


@mcp.tool()
def teams_read(
    conversation_id: str | None = None,
    direction: str | None = None,
    since: float | None = None,
) -> Any:
    """Read messages from the fake Teams channel."""
    params: dict[str, Any] = {}
    if conversation_id:
        params["conversation_id"] = conversation_id
    if direction:
        params["direction"] = direction
    if since is not None:
        params["since"] = since
    return _get("/api/messages", params)


@mcp.tool()
def teams_replies(conversation_id: str | None = None) -> Any:
    """Read bot-direction messages only."""
    return teams_read(conversation_id=conversation_id, direction="bot")


@mcp.tool()
def teams_transcript(conversation_id: str | None = None) -> Any:
    """Full transcript for a conversation."""
    params = {}
    if conversation_id:
        params["conversation_id"] = conversation_id
    return _get("/api/transcript", params)


@mcp.tool()
def teams_join(conversation_id: str | None = None) -> Any:
    """Fire conversationUpdate with membersAdded (welcome flows)."""
    body: dict[str, Any] = {}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return _post("/api/conversation-update", body)


@mcp.tool()
def teams_invoke(
    verb: str = "approve",
    user: str = "alice@example.com",
    conversation_id: str | None = None,
) -> Any:
    """Send an invoke activity (e.g. HITL approve/reject)."""
    body: dict[str, Any] = {"value": {"verb": verb, "user": user}}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return _post("/api/invoke", body)


@mcp.tool()
def teams_members() -> Any:
    """List channel members."""
    return _get("/api/members")


@mcp.tool()
def teams_reset() -> Any:
    """Clear channel state."""
    return _post("/api/reset")


if __name__ == "__main__":
    mcp.run()
