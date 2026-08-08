"""Shared Topaz gate for demos — fail closed."""

from __future__ import annotations

import httpx

TOPAZ = "http://127.0.0.1:8484"


def require(user: str, action: str, path: str = "access") -> None:
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
    except Exception as e:
        raise PermissionError(f"topaz fail-closed: {e}") from e
    if not allowed:
        raise PermissionError(f"denied: {user} cannot {action}")
