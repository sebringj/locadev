"""Fake Slack profile smoke. Skip when :8096 is down."""

import httpx

from conftest import require_port

BASE = "http://127.0.0.1:8096"


def test_slack_post_inject_and_see_messages():
    require_port(8096, "fake-slack")
    with httpx.Client(timeout=15.0) as c:
        c.post(f"{BASE}/api/reset")
        r = c.post(
            f"{BASE}/api/chat.postMessage",
            json={"channel": "C_GENERAL", "text": "bot-hello", "username": "locadev-bot"},
            headers={"Authorization": "Bearer xoxb-test"},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        ts = r.json()["ts"]

        inj = c.post(
            f"{BASE}/api/inject",
            json={
                "channel": "C_GENERAL",
                "text": "user-hello",
                "user": "U_ALICE",
                "username": "alice",
            },
        )
        assert inj.status_code == 200
        assert inj.json()["ok"] is True

        hist = c.post(
            f"{BASE}/api/conversations.history",
            json={"channel": "C_GENERAL", "limit": 10},
        )
        assert hist.status_code == 200
        texts = [m.get("text") for m in hist.json().get("messages") or []]
        assert "bot-hello" in texts
        assert "user-hello" in texts

        # Admin view for assertions (like SendGrid /captured)
        all_m = c.get(f"{BASE}/messages").json()
        assert all_m["count"] >= 2
        dirs = {m.get("direction") for m in all_m["messages"]}
        assert "bot" in dirs and "user" in dirs

        ui = c.get(f"{BASE}/ui")
        assert ui.status_code == 200
        assert "bot-hello" in ui.text
        assert "user-hello" in ui.text

        # update by ts
        up = c.post(
            f"{BASE}/api/chat.update",
            json={"channel": "C_GENERAL", "ts": ts, "text": "bot-hello-edited"},
        )
        assert up.json()["ok"] is True
