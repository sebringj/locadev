# Fake Slack

Local Slack **Web API–shaped** surface for tests — no workspace, no OAuth.

## See messages (test parity)

| Surface | URL |
|---------|-----|
| **HTML viewer** | http://127.0.0.1:8096/ui |
| **JSON dump** | http://127.0.0.1:8096/messages |
| Filter | `/messages?channel=C_GENERAL&direction=user` |

Same idea as fake SendGrid `/captured` and fake-teams `/api/messages`.

## Web API subset

| Endpoint | Purpose |
|----------|---------|
| `POST /api/chat.postMessage` | bot/app posts a message |
| `POST /api/conversations.history` | read channel history |
| `POST /api/conversations.list` | list channels |
| `POST /api/auth.test` | token check (always ok) |
| `POST /api/chat.update` / `chat.delete` | edit/delete by `ts` |
| `POST /api/inject` | simulate a **user** message (not real Slack) |

Any `Authorization: Bearer …` accepted.

## Profile

```bash
docker compose -p locadev --profile slack up -d --build
# or: ./scripts/start.sh slack
```

Port **8096**. Env for clients: `SLACK_API_BASE=http://127.0.0.1:8096` (point the SDK `base_url` / custom endpoint if supported).

## Example

```bash
curl -s -X POST http://127.0.0.1:8096/api/chat.postMessage \
  -H 'Content-Type: application/json' \
  -d '{"channel":"C_GENERAL","text":"hello from bot"}'

curl -s -X POST http://127.0.0.1:8096/api/inject \
  -H 'Content-Type: application/json' \
  -d '{"channel":"C_GENERAL","text":"hi from alice","username":"alice"}'

curl -s http://127.0.0.1:8096/messages | jq .
open http://127.0.0.1:8096/ui
```
