import httpx

from conftest import AISEARCH, require_port


def test_aisearch_create_and_search():
    require_port(8800, "AI Search")
    with httpx.Client(timeout=30.0) as c:
        h = c.get(f"{AISEARCH}/health")
        assert h.status_code == 200
        idx = {
            "name": "smoke-index",
            "fields": [
                {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
                {"name": "title", "type": "Edm.String", "searchable": True},
                {
                    "name": "contentVector",
                    "type": "Collection(Edm.Single)",
                    "dimensions": 3,
                    "searchable": False,
                },
            ],
        }
        r = c.post(f"{AISEARCH}/indexes", json=idx)
        assert r.status_code < 400
        docs = {
            "value": [
                {
                    "@search.action": "upload",
                    "id": "1",
                    "title": "hello locadev",
                    "contentVector": [0.1, 0.2, 0.3],
                }
            ]
        }
        # OData path
        ir = c.post(f"{AISEARCH}/indexes('smoke-index')/docs/search.index", json=docs)
        assert ir.status_code in (200, 207)
        sr = c.post(
            f"{AISEARCH}/indexes('smoke-index')/docs/search.post.search",
            json={"search": "hello", "top": 5},
        )
        assert sr.status_code == 200
        assert "value" in sr.json()
