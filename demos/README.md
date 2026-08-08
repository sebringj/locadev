# demos

Ways to prove locadev is working.

## 1. Playground web app (recommended)

DaisyUI mini-apps in one process — health board, blob, Service Bus, bridge, PGlite, Redis, Topaz.

```bash
make playground
# → http://127.0.0.1:19191
```

See [playground/README.md](./playground/README.md).

## 2. CLI scripts (Topaz-gated patterns)

| Script | Service |
|--------|---------|
| `blob_artifacts.py` | Azurite |
| `servicebus_events.py` | Service Bus topic |
| `pglite_notes.py` | PGlite |
| `foundry_chat_embed.py` | Bridge |
| `cosmos_chat_history.py` | Cosmos (profile) |
| `s3_objects.py` | MiniStack (profile) |
| `test_policy_gate.py` | Topaz only |

```bash
cd demos
source ../.venv/bin/activate   # or project venv with tests/requirements.txt
python blob_artifacts.py
```

Policy users: `alice@example.com` (editor) / `bob@example.com` (viewer).
