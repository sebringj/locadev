"""locadev playground — small daisyUI web app that exercises core stack services.

Run on the Docker host (not inside the stack):
  uvicorn app:app --host 127.0.0.1 --port 19191
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import services

app = FastAPI(title="locadev-playground", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# flash via query: ?flash=...&ok=1
def _flash(request: Request) -> dict[str, Any] | None:
    msg = request.query_params.get("flash")
    if not msg:
        return None
    return {"msg": msg, "ok": request.query_params.get("ok", "1") == "1"}


def _redirect(msg: str, ok: bool = True) -> RedirectResponse:
    from urllib.parse import quote

    return RedirectResponse(
        url=f"/?flash={quote(msg)}&ok={'1' if ok else '0'}",
        status_code=303,
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> Any:
    services_board = services.health_board()
    try:
        blobs = services.blob_list()
    except Exception:
        blobs = []
    try:
        notes = services.pglite_notes()
    except Exception:
        notes = []
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "services": services_board,
            "blobs": blobs,
            "notes": notes,
            "flash": _flash(request),
        },
    )


@app.get("/api/health")
def api_health() -> Any:
    board = services.health_board()
    return {
        "status": "ok" if all(s["ok"] for s in board) else "degraded",
        "services": board,
    }


@app.post("/topaz")
def topaz_check(
    user: str = Form(...),
    action: str = Form(...),
) -> RedirectResponse:
    r = services.topaz_require(user, action)
    if r.get("error"):
        return _redirect(f"topaz error: {r['error']}", ok=False)
    return _redirect(
        f"topaz: {user} action={action} → {'ALLOWED' if r['allowed'] else 'DENIED'}",
        ok=bool(r["allowed"]) or action == "read",
    )


@app.post("/redis")
def redis_demo(
    key: str = Form("locadev:playground"),
    value: str = Form("hello"),
) -> RedirectResponse:
    try:
        r = services.redis_ping_set_get(key, value)
        return _redirect(f"redis ok ping={r['ping']} {key}={r['got']!r}")
    except Exception as e:
        return _redirect(f"redis failed: {e}", ok=False)


@app.post("/blob")
async def blob_upload(
    name: str = Form("demo.txt"),
    text: str = Form(""),
    file: UploadFile | None = File(None),
) -> RedirectResponse:
    try:
        if file and file.filename:
            data = await file.read()
            name = name or file.filename
        else:
            data = (text or "empty").encode("utf-8")
        services.blob_upload(name, data)
        return _redirect(f"blob uploaded: {name} ({len(data)} bytes)")
    except Exception as e:
        return _redirect(f"blob failed: {e}", ok=False)


@app.post("/bus/send")
def bus_send(body: str = Form(...)) -> RedirectResponse:
    try:
        services.sb_send(body)
        return _redirect(f"service bus sent to app-work-queue: {body[:80]!r}")
    except Exception as e:
        return _redirect(f"bus send failed: {e}", ok=False)


@app.post("/bus/receive")
def bus_receive() -> RedirectResponse:
    try:
        msg = services.sb_receive()
        if msg is None:
            return _redirect("service bus: no message (timeout)", ok=True)
        return _redirect(f"service bus received: {msg[:120]!r}")
    except Exception as e:
        return _redirect(f"bus receive failed: {e}", ok=False)


@app.post("/chat")
def chat(prompt: str = Form(...)) -> RedirectResponse:
    try:
        reply = services.bridge_chat(prompt)
        return _redirect(f"chat: {reply[:200]}")
    except Exception as e:
        return _redirect(f"chat failed: {e}", ok=False)


@app.post("/embed")
def embed(text: str = Form(...)) -> RedirectResponse:
    try:
        r = services.bridge_embed(text)
        return _redirect(f"embed dim={r['dim']} preview={r['preview']}")
    except Exception as e:
        return _redirect(f"embed failed: {e}", ok=False)


@app.post("/notes")
def notes_add(body: str = Form(...)) -> RedirectResponse:
    try:
        nid = services.pglite_add_note(body)
        return _redirect(f"pglite note inserted id={nid}")
    except Exception as e:
        return _redirect(f"pglite failed: {e}", ok=False)


@app.get("/api/json/{feature}")
def api_json(feature: str) -> Any:
    """JSON surface for scripted checks."""
    try:
        if feature == "health":
            return api_health()
        if feature == "notes":
            return {"notes": services.pglite_notes()}
        if feature == "blobs":
            return {"blobs": services.blob_list()}
        if feature == "topaz":
            return {
                "alice_write": services.topaz_require("alice@example.com", "write"),
                "bob_write": services.topaz_require("bob@example.com", "write"),
            }
        return JSONResponse({"error": "unknown feature"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)
