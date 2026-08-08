from conftest import COSMOS, COSMOS_KEY, require_port


def test_cosmos_health_or_sdk():
    require_port(8081, "Cosmos")
    # vNext is HTTP; try a simple request first
    import httpx

    with httpx.Client(timeout=10.0, verify=False) as c:
        r = c.get(f"{COSMOS}/")
        # emulator may return various status codes once listening
        assert r.status_code < 500 or r.status_code in (401, 404, 200)
