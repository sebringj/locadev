"""Fake SendGrid capture — nothing leaves the machine."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="locadev-mail")

_captured: list[dict[str, Any]] = []
_counter = 0


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "captured": len(_captured)}


@app.post("/v3/mail/send")
async def send_mail(body: dict[str, Any] | None = None) -> Response:
    global _counter
    body = body or {}
    _counter += 1
    try:
        from_email = ""
        if isinstance(body.get("from"), dict):
            from_email = body["from"].get("email") or ""
        tos: list[str] = []
        subject = body.get("subject") or ""
        for p in body.get("personalizations") or []:
            if not isinstance(p, dict):
                continue
            if p.get("subject"):
                subject = p["subject"]
            for t in p.get("to") or []:
                if isinstance(t, dict) and t.get("email"):
                    tos.append(t["email"])
        html = ""
        for c in body.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "text/html" and c.get("value"):
                html = c["value"]
                break
            if c.get("value") and not html:
                html = c["value"]
        _captured.append(
            {
                "received_at": _counter,
                "from": from_email,
                "to": tos,
                "subject": subject,
                "body": html,
            }
        )
    except Exception:
        # Parse defensively — malformed body must not 500
        _captured.append(
            {
                "received_at": _counter,
                "from": "",
                "to": [],
                "subject": "",
                "body": "",
                "raw": body,
            }
        )
    return Response(status_code=202, headers={"X-Message-Id": f"locadev-{_counter}"})


@app.get("/captured")
def get_captured() -> list[dict[str, Any]]:
    return list(_captured)


@app.delete("/captured")
def clear_captured() -> dict[str, int]:
    n = len(_captured)
    _captured.clear()
    return {"cleared": n}
