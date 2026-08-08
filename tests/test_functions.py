"""Azure Functions sample (profile functions). Skip when :7071 is down."""

import time

import httpx

from conftest import require_port

BASE = "http://127.0.0.1:7071"


def test_functions_ping_and_http_queue_path():
    require_port(7071, "Azure Functions")
    with httpx.Client(timeout=30.0) as c:
        # Host can take a few seconds after container start
        last_err = None
        for _ in range(20):
            try:
                r = c.get(f"{BASE}/api/ping")
                if r.status_code == 200:
                    break
            except Exception as e:
                last_err = e
            time.sleep(1.5)
        else:
            raise AssertionError(f"functions host never ready: {last_err}")

        body = r.json()
        assert body.get("status") == "ok"

        h = c.get(f"{BASE}/api/httpHello", params={"name": "pytest"})
        assert h.status_code == 200, h.text
        data = h.json()
        assert data.get("ok") is True
        assert data.get("enqueued") is True
        assert data.get("storage") == "azurite"

        # queue worker should drain into /api/processed
        found = False
        for _ in range(15):
            p = c.get(f"{BASE}/api/processed")
            assert p.status_code == 200
            items = p.json().get("items") or []
            if any("pytest" in (it.get("body") or "") for it in items):
                found = True
                break
            time.sleep(1)
        assert found, "queue message was not processed via Azurite"
