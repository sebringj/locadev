import httpx

from conftest import PGLITE, require_port


def test_pglite_select_and_vector():
    require_port(5433, "PGlite")
    with httpx.Client(timeout=10.0) as c:
        h = c.get(f"{PGLITE}/health")
        assert h.status_code == 200
        assert h.json()["backend"] == "pglite"
        r = c.post(f"{PGLITE}/sql", json={"sql": "select 1 as n", "params": []})
        assert r.status_code == 200
        rows = r.json()["rows"]
        assert rows and (rows[0].get("n") == 1 or list(rows[0].values())[0] == 1)
        # vector extension present after seed
        v = c.post(
            f"{PGLITE}/sql",
            json={
                "sql": "select extname from pg_extension where extname = 'vector'",
                "params": [],
            },
        )
        assert v.status_code == 200
        assert v.json()["rows"]
