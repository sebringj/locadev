# Fake Discord

Local Discord **REST v9/v10–shaped** surface for tests — no real guild, no Gateway.

## See messages (test parity)

| Surface | URL |
|---------|-----|
| **HTML viewer** | http://127.0.0.1:8097/ui |
| **JSON dump** | http://127.0.0.1:8097/messages |
| Filter | `/messages?channel_id=c_general&direction=user` |

Same idea as fake Slack `/ui` + `/messages` and fake Teams `/api/messages`.

## REST subset

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v10/channels/{id}/messages` | bot creates a message |
| `GET /api/v10/channels/{id}/messages` | list history (newest first) |
| `PATCH/DELETE .../messages/{id}` | edit / delete |
| `GET /api/v10/guilds/{id}/channels` | list channels |
| `GET /api/v10/users/@me` | bot user stub |
| `POST /api/inject` | simulate a **user** message |

Any `Authorization: Bot …` accepted.

Seed channels: `c_general`, `c_dev`, `c_dm_alice`.

## Profile

```bash
docker compose -p locadev --profile discord up -d --build
# or: ./scripts/start.sh discord
```

Port **8097**. Env: `DISCORD_API_BASE=http://127.0.0.1:8097`

## Example

```bash
curl -s -X POST http://127.0.0.1:8097/api/v10/channels/c_general/messages \
  -H 'Authorization: Bot locadev' \
  -H 'Content-Type: application/json' \
  -d '{"content":"hello from bot"}'

curl -s -X POST http://127.0.0.1:8097/api/inject \
  -H 'Content-Type: application/json' \
  -d '{"channel_id":"c_general","content":"hi from alice","username":"alice"}'

curl -s http://127.0.0.1:8097/messages | jq .
open http://127.0.0.1:8097/ui
```
