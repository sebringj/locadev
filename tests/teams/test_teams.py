"""Teams profile tests. Start with ECHO_BOT_BRAIN= empty for plain echo."""

import httpx
import pytest

from conftest import TEAMS, require_port


@pytest.fixture(autouse=True)
def _need_teams():
    require_port(3979, "fake-teams")


def test_inject_echo():
    with httpx.Client(timeout=30.0) as c:
        c.post(f"{TEAMS}/api/reset")
        r = c.post(f"{TEAMS}/api/inject", json={"text": "ping-teams"})
        assert r.status_code == 200
        # bot should have replied
        msgs = c.get(f"{TEAMS}/api/messages", params={"direction": "bot"}).json()
        texts = " ".join(m.get("text") or "" for m in msgs.get("messages") or [])
        assert "ping-teams" in texts or "echo" in texts.lower()


def test_conversation_update_welcome():
    with httpx.Client(timeout=30.0) as c:
        c.post(f"{TEAMS}/api/reset")
        r = c.post(
            f"{TEAMS}/api/conversation-update",
            json={"membersAdded": [{"id": "user-bob", "name": "Bob"}]},
        )
        assert r.status_code == 200
        msgs = c.get(f"{TEAMS}/api/messages", params={"direction": "bot"}).json()
        texts = " ".join(m.get("text") or "" for m in msgs.get("messages") or [])
        assert "Welcome" in texts or "Bob" in texts
