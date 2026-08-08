# locadev playground

Small **DaisyUI** web app (Tailwind + DaisyUI CDN) that exercises **core** locadev services from the Docker host.

| Panel | Service |
|-------|---------|
| Service board | ports + health HTTP |
| Topaz RBAC | authorizer `:8484` |
| Redis | `:6380` |
| Azurite blob | `:10000` |
| Service Bus | queue `app-work-queue` |
| Foundry chat / embed | bridge `:8090` |
| PGlite notes | HTTP `:5433` |

## Run

```bash
# stack up first
start-docker   # if needed
make up && make verify

cd demos/playground
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 19191
```

Or from repo root:

```bash
make playground
```

Open **http://127.0.0.1:19191**

JSON helpers: `/api/health`, `/api/json/topaz`, `/api/json/notes`, `/api/json/blobs`

## Notes

- Runs **on the host**, not inside compose (uses `127.0.0.1` endpoints from `sandbox.env.example`).
- Optional profiles (Cosmos, S3, mail, …) are not wired here; use CLI demos in `demos/*.py` when those profiles are up.
