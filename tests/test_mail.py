import httpx

from conftest import MAIL, require_port


def test_mail_capture():
    require_port(8095, "Mail")
    with httpx.Client(timeout=10.0) as c:
        c.delete(f"{MAIL}/captured")
        r = c.post(
            f"{MAIL}/v3/mail/send",
            json={
                "from": {"email": "from@example.com"},
                "personalizations": [{"to": [{"email": "to@example.com"}]}],
                "subject": "locadev smoke",
                "content": [{"type": "text/plain", "value": "hi"}],
            },
        )
        assert r.status_code == 202
        assert r.headers.get("X-Message-Id")
        cap = c.get(f"{MAIL}/captured").json()
        assert any(m.get("subject") == "locadev smoke" for m in cap)
