"""Fake Discord profile smoke. Skip when :8097 is down."""

import httpx

from conftest import require_port

BASE = "http://127.0.0.1:8097"


def test_discord_post_inject_and_see_messages():
    require_port(8097, "fake-discord")
    with httpx.Client(timeout=15.0) as c:
        c.post(f"{BASE}/api/reset")
        r = c.post(
            f"{BASE}/api/v10/channels/c_general/messages",
            json={"content": "bot-hello"},
            headers={"Authorization": "Bot locadev"},
        )
        assert r.status_code == 200
        mid = r.json()["id"]
        assert r.json()["content"] == "bot-hello"

        inj = c.post(
            f"{BASE}/api/inject",
            json={
                "channel_id": "c_general",
                "content": "user-hello",
                "username": "alice",
            },
        )
        assert inj.status_code == 200
        assert inj.json()["ok"] is True

        hist = c.get(f"{BASE}/api/v10/channels/c_general/messages")
        assert hist.status_code == 200
        texts = [m.get("content") for m in hist.json()]
        assert "bot-hello" in texts
        assert "user-hello" in texts

        all_m = c.get(f"{BASE}/messages").json()
        assert all_m["count"] >= 2
        dirs = {m.get("direction") for m in all_m["messages"]}
        assert "bot" in dirs and "user" in dirs

        ui = c.get(f"{BASE}/ui")
        assert ui.status_code == 200
        assert "bot-hello" in ui.text
        assert "user-hello" in ui.text

        up = c.patch(
            f"{BASE}/api/v10/channels/c_general/messages/{mid}",
            json={"content": "bot-hello-edited"},
        )
        assert up.status_code == 200
        assert up.json()["content"] == "bot-hello-edited"
