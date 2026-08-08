# Build `locadev` from scratch - instructions for an AI

You are building a **self-contained, dockerized local cloud (Azure + AWS)** that application
services can be developed and tested against with **no cloud subscription**. Everything below is
derived from a working pattern; treat the invariants and gotchas as requirements, not suggestions -
each gotcha is a bug that was already paid for once.

**This repo is `locadev`.** Do not name the project, compose stack, network, containers, or docs
after any other sandbox (`ai-env-local-sandbox`, AECOM RW/FA, etc.). Consumer-facing examples stay
generic so any client app can point env at this stack.

Deliverable: a git repo whose `docker compose up -d --build` yields a running local Azure/AWS surface,
plus health-gate scripts, smoke tests, and app-pattern demos that pass.

**Primary host today: macOS** (Docker Desktop). Linux is first-class. Windows/WSL is optional
background; do not make PowerShell or WSL the main path.

---

## 0. Mission and non-negotiables

**Goal.** A client repo becomes a sandbox client by **changing env values only - never code**. Every
emulated service must present the same API shape and SDK contract as the real thing, so the move to a
real cloud sandbox later is a connection-string swap.

**Framing to preserve in the README.** This is an **interim** solution, not a true sandbox. A real
isolated Azure subscription gives real Entra RBAC, managed identity, real AI Search, Cosmos global
distribution. This stack trades cloud fidelity for **free, offline, instant, no-subscription**
iteration. Say so plainly; do not oversell fidelity.

**Host rule (macOS / Linux).** Run Docker Engine natively (Docker Desktop on Mac). Run the stack,
tests, and consuming repos on the same host that publishes the ports. Prefer `localhost` / `127.0.0.1`
from the host and Docker service names from containers. Use
`extra_hosts: ["host.docker.internal:host-gateway"]` only when a container must reach a process on the
host (e.g. host Ollama).

**Security rule.** Do not port-sweep corporate networks or enumerate firewalls from scripts. Health
checks probe **only** the ports this stack publishes, on `127.0.0.1`, via simple TCP/`curl` in
`scripts/verify.sh`.

**Honesty rule.** Where an emulator only approximates the real service, document the approximation
next to the code (semantic reranking, OData filters, Topaz vs Azure RBAC). Never let a limitation be
discovered by a consumer at runtime.

**Database rule — PGlite for app Postgres.** Application Postgres in this stack is **PGlite**
([electric-sql/pglite](https://github.com/electric-sql/pglite)): a WASM Postgres build with
**pgvector** support, no heavy `postgres` server container for app data. A thin FastAPI adapter
(`pglite/`) exposes a small HTTP SQL API **and** (optional) a wire-compatible gateway for clients that
still speak `psycopg`/`Npgsql` against a host port. Document clearly:

- PGlite is for **app** data (agent config, chat history demos, sample services).
- The Azure **Service Bus emulator** still needs its own **internal MSSQL** container; that is not
  the app DB and **must not** be published as one.
- If a consumer truly needs a full multi-connection Postgres server later, that can be a future
  profile; default is PGlite.

---

## 1. Prerequisites

- Docker Desktop (macOS) or Docker Engine (Linux); `docker compose` v2.
- Python 3.12 for adapter services (images built from `python:3.12-slim` or Node where PGlite needs it).
- Optional for real LLM output: host **Ollama**, or the **Claude Code CLI** authed (`claude auth login`).
- Optional GPU for the dockerized Ollama profile: NVIDIA toolkit on Linux; on Mac, Apple Silicon uses
  host Ollama instead of the GPU compose reservation.
- Node.js 20+ **only if** the PGlite service is implemented in Node rather than a Python wrapper around
  a Node subprocess — pick one stack and stick to it (recommended: small Node service for PGlite +
  Python for the Azure-shaped adapters).

---

## 2. Target repo layout

Create exactly this structure.

```
.env.example              docker compose ${...} substitution values
.gitignore                never commit real env files
.mcp.json                 repo-local MCP so Claude can drive the fake-Teams channel
Makefile                  macOS/Linux convenience targets
README.md                 the doc described in section 12
docker-compose.yml        all services, optional ones behind profiles
sandbox.env.example       the CONSUMER contract: values to paste into a client repo's .env

infra/Config.json         Service Bus emulator entity declarations
infra/aws-init/01-seed-s3.sh   MiniStack S3 seed (LocalStack-compatible init)

bridge/                   Azure-OpenAI / Foundry surface -> Claude | Ollama | fake
  app.py  harness.py  Dockerfile  requirements.txt  README.md
aisearch/                 Azure AI Search emulator, Qdrant-backed
  app.py  Dockerfile  requirements.txt  README.md
mail/                     fake SendGrid capture
  app.py  Dockerfile  requirements.txt  README.md
fake_teams/               local Teams channel (control plane)
  app.py  Dockerfile  requirements.txt
echo_bot/                 the bot behind fake-teams
  app.py  Dockerfile  requirements.txt
mcp_server/               host-run MCP exposing the fake-teams channel as tools
  server.py  requirements.txt

pglite/                   PGlite app database (HTTP + optional PG-wire gateway)
  server.mjs (or app.py)  Dockerfile  package.json  README.md
  seed.sql                demo schema + rows for sample_service / demos

topaz/config.yaml         Topaz v2 config
topaz/policy/.manifest    bundle roots
topaz/policy/access.rego  data-plane RBAC
topaz/policy/approval.rego  HITL approval RBAC
topaz/policy/data.json    role + permission data

sample_service/           minimal FastAPI example client (app.py, requirements.txt)

scripts/start.sh          interactive checkbox launcher (bash, no deps)
scripts/verify.sh         TCP health gate (macOS/Linux)

tests/                    bare-connectivity smoke tests, one per service
demos/                    Topaz-gated app-pattern demos + their tests
tests/teams/              tests for the Teams profile
```

Do **not** add Windows-only `scripts/*.ps1` as required deliverables. If someone later needs them,
they can wrap `scripts/*.sh`; Mac and Linux are the supported path.

---

## 3. Port map - build to this table exactly

Ports were chosen to dodge real clashes. Do not "tidy" them without a documented reason.

| Service | Container | Host port | Notes |
|---|---|---|---|
| Azurite blob | 10000 | **10000** | |
| Azurite queue | 10001 | **10101** | 10001 is commonly taken on dev boxes |
| Azurite table | 10002 | **10002** | |
| Service Bus AMQP | 5672 | **5672** | real AMQP |
| Service Bus mgmt/health | 5300 | **5300** | `EMULATOR_HTTP_PORT` |
| mssql (SB backend) | 1433 | **not published** | internal only; not an app DB |
| Foundry bridge | 8090 | **8090** | Azure OpenAI URL shape |
| PGlite HTTP | 5433 | **5433** | app SQL over HTTP |
| PGlite PG-wire (optional) | 5432 | **5432** | when gateway enabled; leave free if unused |
| Redis | 6379 | **6380** | host 6379 often taken by local redis |
| Topaz REST authorizer | 8383 | **8484** | leaves 8383 free for a second Topaz |
| Topaz gRPC | 8282 | **8485** | |
| Cosmos vNext | 8081, 1234 | **8081, 1234** | profile `cosmos` |
| MiniStack AWS gateway | 4566 | **4566** | profile `aws` |
| Key Vault (lowkey-vault) | 8443 | **8443** | profile `kv` |
| Qdrant | 6333 | **6333** | profile `search` |
| AI Search emulator | 8800 | **8800** | profile `search` |
| Fake SendGrid | 8095 | **8095** | profile `mail` |
| fake-teams | 3979 | **3979** | profile `teams` |
| echo-bot | 3978 | **3978** | profile `teams` |
| sample_service | 8080 | **18080** | profile `sample` |

Compose project name: **`locadev`**. Network: a single bridge network named **`locadev`**. Container
names: **`locadev-<service>`** (`locadev-azurite`, `locadev-bridge`, ...). Named volumes:
`azurite-data`, `mssql-data`, `pglite-data`, `ministack-data`, `ollama-data`, `qdrant-data`.

**Core services (always started, no profile):** azurite, mssql, servicebus, bridge, topaz, pglite, redis.
**Profiles:** `teams`, `aws`, `cosmos`, `search`, `kv`, `ollama`, `mail`, `sample`.

There is **no** profile that builds a sibling application monorepo. This repo stays self-contained;
`sample_service` is the only in-repo "consumer app" demo service.

---

## 4. Phase 1 - skeleton and env

### `.gitignore`
```
# never commit real env files; *.example files are the only tracked env files
.env
.env.*
!.env.example
.venv/
node_modules/
__pycache__/
*.pyc
.pytest_cache/
*.log
pglite-data/
```

### `.env.example`
Read by compose for `${...}` substitution. Copy to `.env` on first run.
```
ACCEPT_EULA=Y
MSSQL_SA_PASSWORD=Sandbox!Dev2026
EMULATOR_HTTP_PORT=5300
SQL_WAIT_INTERVAL=20

CHAT_BACKEND=fake
EMB_BACKEND=fake
OLLAMA_BASE=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBED_DIM=1536

#ECHO_BOT_BRAIN=

SEED_BUCKET=locadev-demo
PGLITE_DATA_DIR=/data
```
Comment in the file that `ACCEPT_EULA=Y` acknowledges the Microsoft EULAs for **both** SQL Server for
Linux and the Service Bus emulator (dev/test only, no SLA), and that `CHAT_BACKEND=claude-cli` is
**host-only**.

---

## 5. Phase 2 - core compose services

### azurite
Image `mcr.microsoft.com/azure-storage/azurite:latest`.
Command: `azurite --blobHost 0.0.0.0 --queueHost 0.0.0.0 --tableHost 0.0.0.0 --location /data --skipApiVersionCheck`.
Ports `10000:10000`, `10101:10001`, `10002:10002`. Volume `azurite-data:/data`.

### mssql (Service Bus backend only)
Image `mcr.microsoft.com/mssql/server:2022-latest`. **Do not publish 1433** - it is the emulator's
backing store, not an app DB. Env `ACCEPT_EULA`, `MSSQL_SA_PASSWORD`. Volume `mssql-data:/var/opt/mssql`.
Network alias `mssql`.

### servicebus
Image `mcr.microsoft.com/azure-messaging/servicebus-emulator:latest`, `pull_policy: always`.
Ports `5672:5672` (AMQP) and `5300:${EMULATOR_HTTP_PORT:-5300}`.
Env: `SQL_SERVER: mssql`, `MSSQL_SA_PASSWORD`, `ACCEPT_EULA`, `EMULATOR_HTTP_PORT`, `SQL_WAIT_INTERVAL`.
Mount `./infra/Config.json:/ServiceBus_Emulator/ConfigFiles/Config.json`. `depends_on: [mssql]`.
Network alias `servicebus-emulator`.

**The emulator only creates entities declared in `Config.json`.** There is no runtime create-queue.
Adding an entity means editing this file and restarting the emulator.

### `infra/Config.json` (verbatim shape — generic demo entities)
```json
{
  "UserConfig": {
    "Namespaces": [
      {
        "Name": "sbemulatorns",
        "Queues": [
          { "Name": "app-work-queue",
            "Properties": { "DeadLetteringOnMessageExpiration": false, "DefaultMessageTimeToLive": "PT1H",
                            "LockDuration": "PT1M", "MaxDeliveryCount": 3,
                            "RequiresDuplicateDetection": false, "RequiresSession": false } },
          { "Name": "dev-ingestion-queue",
            "Properties": { "DeadLetteringOnMessageExpiration": false, "DefaultMessageTimeToLive": "PT1H",
                            "LockDuration": "PT5M", "MaxDeliveryCount": 3,
                            "RequiresDuplicateDetection": false, "RequiresSession": false } }
        ],
        "Topics": [
          { "Name": "emailrequest",
            "Properties": { "DefaultMessageTimeToLive": "PT1H", "RequiresDuplicateDetection": false },
            "Subscriptions": [ { "Name": "emailrequest-sub",
              "Properties": { "DeadLetteringOnMessageExpiration": false, "DefaultMessageTimeToLive": "PT1H",
                              "LockDuration": "PT1M", "MaxDeliveryCount": 3, "RequiresSession": false } } ] },
          { "Name": "app-events",
            "Properties": { "DefaultMessageTimeToLive": "PT1H", "RequiresDuplicateDetection": false },
            "Subscriptions": [ { "Name": "app-events-sub",
              "Properties": { "DeadLetteringOnMessageExpiration": false, "DefaultMessageTimeToLive": "PT1H",
                              "LockDuration": "PT1M", "MaxDeliveryCount": 3, "RequiresSession": false } } ] }
        ]
      }
    ],
    "Logging": { "Type": "File" }
  }
}
```
**Gotcha:** `Logging` is a **sibling of `Namespaces` under `UserConfig`** - not nested inside a namespace.
Getting this wrong makes the emulator fail to load the config.

### pglite (app database)
Build `./pglite`. Image based on `node:20-slim` (or equivalent) running `@electric-sql/pglite` with the
**vector** extension enabled. Persist the data directory on volume `pglite-data:/data`.

**HTTP surface (required)** — so smoke tests and demos do not depend on wire protocol quirks:

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | `{status, backend: "pglite", extensions: ["vector"]}` |
| POST | `/sql` | body `{ "sql": "...", "params": [] }` → `{ "rows", "fields", "rowCount" }` |
| POST | `/exec` | multi-statement script (seed), returns `{ "ok": true }` or error |
| GET | `/ready` | 200 only after seed applied |

Port mapping: **`5433:5433`** for HTTP.

**Optional PG-wire gateway:** if implemented (e.g. community TCP bridge around PGlite), publish
**`5432:5432`** and document connection as
`postgresql://locadev:locadev@127.0.0.1:5432/locadev`. If wire is not implemented in v1, omit 5432
from compose and document HTTP-only; do not pretend wire works.

**Seed:** on first boot (empty data dir), run `pglite/seed.sql`:
- `CREATE EXTENSION IF NOT EXISTS vector;`
- minimal demo tables, e.g. `notes (id text primary key, body text, embedding vector(1536))` and
  `chat_messages (id text primary key, role text, content text, created_at timestamptz)`.
- insert a few deterministic rows so demos are not empty.

**Gotchas:**
- PGlite is single-user / single-connection in spirit; do not assume heavy concurrent pool behavior
  like a full Postgres server.
- Embeddings demos must use the same `EMBED_DIM` as the bridge (default 1536).
- Consumers that hard-require multi-connection server Postgres should treat PGlite as a **local
  stand-in** and plan a real server for staging.

Compose env: `PGLITE_DATA_DIR=/data`, port `5433`. Alias `pglite`. Other containers reach it as
`http://pglite:5433`.

### redis
Image `redis:7`. Port **`6380:6379`**. Alias `redis` so containers use `redis:6379`.

### topaz
Image `ghcr.io/aserto-dev/topaz:latest`, command `["run","--config-file","/config/config.yaml"]`.
Ports `8484:8383` (REST) and `8485:8282` (gRPC). Mount `./topaz/config.yaml:/config/config.yaml` and
`./topaz/policy:/policy`.

`topaz/config.yaml`:
```yaml
version: 2

logging:
  prod: false
  log_level: info

directory:
  db_path: /tmp/directory.db

api:
  services:
    authorizer:
      grpc:
        listen_address: "0.0.0.0:8282"
      gateway:
        listen_address: "0.0.0.0:8383"
        http: true

opa:
  instance_id: "-"
  graceful_shutdown_period_seconds: 2
  local_bundles:
    paths:
      - /policy
    skip_verification: true
  config:
    bundles: {}
```
**Gotchas:** Topaz **v2** config has **no top-level `authentication:` key**; local policy is loaded via
`opa.local_bundles.paths`; the REST gateway needs `http: true`.

`topaz/policy/.manifest`:
```json
{ "roots": ["access", "approval"] }
```

`topaz/policy/access.rego`:
```rego
package access

import rego.v1

default allowed := false

allowed if {
  some role in data.access.roles[input.resource.user]
  role in data.access.permissions[input.resource.action]
}
```

`topaz/policy/approval.rego`: identical shape, `package approval`, reading `data.approval.*`.

`topaz/policy/data.json`:
```json
{
  "access": {
    "roles": { "alice@example.com": ["editor"], "bob@example.com": ["viewer"] },
    "permissions": { "write": ["editor"], "read": ["editor","viewer"], "infer": ["editor","viewer"] }
  },
  "approval": {
    "roles": { "alice@example.com": ["approver"], "bob@example.com": ["viewer"] },
    "permissions": { "approve": ["approver"], "reject": ["approver"], "view": ["approver","viewer"] }
  }
}
```

**Authorization call contract** every consumer uses - `POST /api/v2/authz/is`:
```json
{
  "identity_context": { "type": "IDENTITY_TYPE_NONE", "identity": "" },
  "policy_context":   { "path": "access", "decisions": ["allowed"] },
  "resource_context": { "user": "alice@example.com", "action": "write" }
}
```
Decision is read as `response["decisions"][0]["is"]`. Callers must **fail closed** on any error, and
treat "Topaz not configured" as ungated only if that is an explicit local choice.

Document the honest framing: Topaz stands in for **application-level fine-grained RBAC**, not Azure
control-plane role assignments. There is no local emulator for Entra/Azure RBAC.

**Gate 1.** `docker compose up -d --build` brings up all seven core services; `docker compose ps` shows
them healthy; `curl http://localhost:5300/health` and `http://localhost:8090/health` and
`http://localhost:5433/health` all answer.

---

## 6. Phase 3 - the bridge (Azure OpenAI / Foundry surface)

`bridge/` is a FastAPI app (`python:3.12-slim`, `uvicorn app:app --host 0.0.0.0 --port 8090`).
Requirements: `fastapi==0.115.6`, `uvicorn==0.34.0`, `httpx==0.28.1`, `openai==1.59.6`.

Compose: `build: ./bridge`, port `8090:8090`, env `CHAT_BACKEND`, `EMB_BACKEND`, `OLLAMA_BASE`,
`OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`, `EMBED_DIM`, plus
`extra_hosts: ["host.docker.internal:host-gateway"]` so the container can reach a host Ollama
(especially useful on Mac, where host Ollama is the usual GPU path).

### Endpoints (must match the Azure URL shape exactly)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{status, chat_backend, emb_backend, embed_dim}` |
| POST | `/openai/deployments/{deployment}/chat/completions` | chat |
| POST | `/openai/deployments/{deployment}/embeddings` | embeddings |

The `api-version` query param is accepted with **any** value. The `api-key` header is **ignored**.
Deployment names are accepted **as-is** (`gpt-4.1`, `text-embedding-ada-002`, anything).

### Chat behavior
- Read `messages` (OpenAI shape) and `stream` from the body.
- Backends by `CHAT_BACKEND`:
  - `fake` - deterministic: `FAKE_FOUNDRY[{deployment}]: {last user message, truncated to 200 chars}`.
  - `ollama` - `POST {OLLAMA_BASE}/api/chat` with `stream:false`, `options.temperature:0`; reply is
    `json()["message"]["content"]`.
  - `claude-cli` - shell out to `claude -p`, feeding a flattened prompt on stdin. Roles render as
    `System:` / `User:` / `Assistant:` / `Tool:` blocks joined by blank lines, ending with a bare
    `Assistant:`. Honor `CLAUDE_MODEL`, `CLAUDE_TIMEOUT_S` (default 120). **Host-only** on Mac/Linux;
    a Linux container cannot reach the host's authed `claude` binary, so run the bridge process on the
    host for that mode.
- Non-stream response: full `chat.completion` object - `id`, `object`, `created`, `model` (= deployment),
  `choices[0].message.{role,content}`, `finish_reason: "stop"`, and a `usage` block with word-count
  approximations.
- Stream response: `text/event-stream` emitting **four** frames - a role-delta chunk, a content chunk,
  a `finish_reason: "stop"` chunk, then `data: [DONE]`. Each chunk is `chat.completion.chunk`.
- Any backend failure returns **HTTP 502** with `{"error":{"message":"chat backend (X) failed: ...","type":"bridge_error"}}`.
  Errors must name the backend - no vague failures.

### Embeddings behavior
- Accept `input` as a string or list; return `{"object":"list","model":deployment,"data":[{object,index,embedding}],"usage":{...}}`.
- `EMB_BACKEND=fake` - deterministic vector derived from `sha256(text)`, values mapped into `[-1,1]`.
- `EMB_BACKEND=ollama` - `POST {OLLAMA_BASE}/api/embeddings`, then **project to `EMBED_DIM`**
  (truncate if longer, zero-pad if shorter). Claude has **no embeddings API**, which is why embeddings
  never route to `claude-cli`.
- `EMBED_DIM` defaults to **1536** to match the AI Search index schema and PGlite seed vectors. If a
  consumer's index expects a different dimensionality, `EMBED_DIM` must be changed to match or writes
  will be rejected.
- Failures return 502 naming `EMB_BACKEND`.

### `bridge/harness.py`
An E2E proof that drives the bridge with the **same client apps use** - `openai.AzureOpenAI` with
`azure_endpoint`, a throwaway `api_key`, `api_version="2025-01-01-preview"` - and prints a chat result
and an embedding length. If this passes, an unmodified Azure OpenAI client works against the bridge.

**Backend selection guidance to document:** `fake` = deterministic, runs anywhere, right default for
tests. `ollama` = real offline model, reachable **from the container**, use when a repo needs real
structured output (on Mac, prefer host Ollama + `host.docker.internal`). `claude-cli` = best quality
but **host-only**.

**Gate 2.** `python bridge/harness.py` against a running bridge returns a chat completion and a
1536-length embedding.

---

## 7. Phase 4 - launcher, health gate, Makefile

### `scripts/verify.sh`
Pure bash TCP probe. Prefer `bash` `/dev/tcp` where available; on macOS default bash is old, so use a
portable check (e.g. `nc -z -G 2 127.0.0.1 $port` or `python3 -c` socket connect with 2s timeout) and
document the chosen method. Core failures set a non-zero exit; profile-gated services print `[--]` when
off rather than failing.

Core: Azurite blob 10000, ServiceBus AMQP 5672, bridge 8090, PGlite HTTP 5433, Topaz 8484.
Optional: Cosmos 8081, MiniStack 4566, Key Vault 8443, AI Search 8800, mail 8095, teams 3979.

Header must state it is meant to run **on the Docker host** (macOS or Linux).

### `scripts/start.sh`
An interactive checkbox screen in **pure bash** - no `dialog`, `fzf`, or `gum`. Requirements:
- Core list is always-on and displayed as such.
- One row per optional profile: `teams`, `aws`, `cosmos`, `search`, `kv`, `ollama`, `mail`, `sample`,
  each with a one-line description including its port.
- Keys: up/down or `j`/`k` move, space toggles, `a` all, `n` none, enter launches, `q`/esc quits with
  nothing started.
- Launch runs `docker compose [--profile X]... up -d --build`, echoing the command.
- **Non-interactive path:** `scripts/start.sh teams aws` skips the menu; an unknown profile name exits 2.
- If stdin/stdout is not a TTY, print the non-interactive usage and exit 2 instead of hanging.
- Hide the cursor while drawing and restore it via an `EXIT` trap.

### `Makefile`
Targets: `start` (interactive), `up`, `teams`, `down` (accepts `ARGS=-v`), `verify` (curl the health
endpoints), `test`, `logs`.

**Gate 3.** `bash scripts/verify.sh` prints `Core services OK.` with the core stack up, and `[--]` lines
for profiles that are off.

---

## 8. Phase 5 - optional profiles

### `cosmos` - Cosmos DB vNext emulator
Image `mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-latest`, ports `8081:8081`, `1234:1234`.
**Gotcha:** the vNext gateway is **HTTP on 8081** (the classic emulator was HTTPS). Boot is heavy
(~1-2 min), so it is profile-gated and its tests **skip** when absent. Key is the public well-known
emulator key.

**Mac note:** the Cosmos emulator image is large and slow; if it fails under Docker Desktop resource
limits, document raising memory and that tests skip when the port is down.

### `aws` - MiniStack (local AWS)
Image `ministackorg/ministack:latest`, port `4566:4566`, env `GATEWAY_PORT: 4566` and `S3_PERSIST: "1"`,
volume `ministack-data:/var/lib/ministack`, plus
`./infra/aws-init:/etc/localstack/init/ready.d:ro`.

Why MiniStack: free/MIT LocalStack-shaped gateway on port **4566** with init-directory convention.
Creds are `test`/`test`, region `us-east-1`.

Scope honestly: **S3 only** by default (most local AWS needs here are S3-compatible endpoints via
`boto3` + `endpoint_url`). DynamoDB/SQS/etc. are one compose-env line away when a flow needs them.

`infra/aws-init/01-seed-s3.sh` - `/bin/sh`, `set -e`, exports the test creds, creates
`s3://${SEED_BUCKET:-locadev-demo}` against `http://localhost:4566`, then puts a few objects under a
clear hierarchy, e.g.:
```
demo/acme/project-001/readme.txt
demo/acme/project-001/notes.txt
demo/globex/project-002/report.txt
```
Finish by listing the bucket recursively so the log proves the seed.

### `kv` - Key Vault
Image `nagyesta/lowkey-vault:latest`, port `8443:8443`. Optional because consuming repos fall back to
env vars (`USE_KEY_VAULT=false`).

### `search` - Qdrant + Azure AI Search emulator
`qdrant`: image `qdrant/qdrant:latest`, port `6333:6333`, volume `qdrant-data:/qdrant/storage`, alias `qdrant`.

`aisearch`: build `./aisearch`, port `8800:8800`, env `QDRANT_URL: http://qdrant:6333`,
`depends_on: [qdrant]`. Requirements: `fastapi`, `uvicorn[standard]`, `qdrant-client>=1.9,<2.0`.

The emulator must serve the subset of the Azure AI Search REST surface that
`azure-search-documents >= 11.4.0` actually calls. **Verify the shapes against the installed SDK's
generated code - do not guess.** The SDK builds OData-style paths:

| Method | Path | Meaning |
|---|---|---|
| POST | `/indexes` | create index (name in body) |
| PUT / GET / DELETE | `/indexes('{index}')` | create-or-update / get / delete |
| POST | `/indexes('{index}')/docs/search.index` | upload / merge / mergeOrUpload / delete documents |
| POST | `/indexes('{index}')/docs/search.post.search` | query |
| GET | `/indexes('{index}')/docs('{key}')` | get one document |
| GET | `/indexes('{index}')/docs?search=...` | simple GET query |

Also accept the short slash forms (`/indexes/{index}`, `/docs/index`, `/docs/search`) so repos work
regardless of SDK path style. Implement this as a **catch-all dispatcher** that parses `name('key')`
segments. `api-key` header ignored; `api-version` accepted with any value.

Implementation requirements:
- Parse the posted index schema for: key field (`key: true`, default `id`), the vector field
  (`Collection(Edm.Single)`/`Collection(Edm.Half)` carrying `dimensions`), searchable string fields, and
  the distance metric from `vectorSearch.algorithms[].hnswParameters.metric` (cosine default; map
  euclidean/dotProduct; fall back to cosine for unsupported metrics).
- Create/recreate a Qdrant collection per index. With no vector field, use a size-1 placeholder vector
  so payload-only documents remain queryable by text/filter.
- **Qdrant point ids must be an unsigned int or a UUID** - arbitrary string keys are rejected. Map
  document keys deterministically with `uuid5(fixed_namespace, f"{index}:{key}")` and stash the original
  key in the payload under a private field.
- Document batch: honor `@search.action` (`upload`, `merge`, `mergeOrUpload`, `delete`). `merge` without
  an existing document returns per-item `statusCode: 404`, matching Azure. `merge` without a fresh
  vector keeps the existing vector and merges payloads. Missing vector on upload becomes a zero vector.
  Respond `{"value":[{key,status,errorMessage,statusCode}...]}`, and 207 when the batch failed.
- Query: vector query from the first `vectorQueries[]` entry of kind `vector` (honor its `k`), else a
  text scroll with a naive case-insensitive token-count score over searchable fields. `search` of `*` or
  empty means match-all. Honor `top`, `select`, `queryType`. Emit `@search.score` on every hit, and
  `@search.rerankerScore` when `queryType=semantic`.
- `$filter`: translate only simple `field eq 'value'` conjunctions joined by `and`. Anything more
  complex (`or`, `not`, comparisons, `search.ismatch`, parentheses) is **ignored**, logged, and echoed
  back in the response as an emulator note. Never silently drop a filter.
- `GET /health` reports index names plus Qdrant reachability, degrading rather than failing.

**Documented limitations:** no real L2 semantic reranker (reranker score echoes the hybrid score);
partial OData `$filter`; hybrid RRF fusion approximated by letting vector ANN dominate.

### `mail` - fake SendGrid
Build `./mail`, port `8095:8095`, alias `sendgrid`. FastAPI, in-memory capture, nothing leaves the machine.

| Method | Path | Behavior |
|---|---|---|
| POST | `/v3/mail/send` | capture and return **202** with an `X-Message-Id` header, like real SendGrid |
| GET | `/captured` | every captured message, for assertions |
| DELETE | `/captured` | clear, returns `{"cleared": n}` |
| GET | `/health` | `{status, captured}` |

Capture `from.email`, all `personalizations[].to[].email`, subject (top-level or per-personalization),
and body from `content[].value` preferring `text/html`. Use a **monotonic counter** for `received_at`,
not the wall clock, so ordering and equality stay deterministic in tests. Parse defensively - a
malformed body must not 500.

### `ollama` - real local LLM in Docker
Image `ollama/ollama:latest`, alias `ollama`, volume `ollama-data:/root/.ollama`, no published port
(the bridge reaches it as `http://ollama:11434`).

On **Linux with NVIDIA**: request the host GPU via `deploy.resources.reservations.devices` with
`driver: nvidia`, `count: all`, `capabilities: [gpu]`. On **macOS**: do not rely on that reservation;
prefer host Ollama (`OLLAMA_BASE=http://host.docker.internal:11434`) or run the container CPU-only and
document the tradeoff. First run needs `docker exec locadev-ollama ollama pull <model>` (or host
`ollama pull`).

### `teams` - Teams channel + bot
Purpose: local bot development with **no M365 tenant and no tunnel**.

`fake-teams`: build `./fake_teams`, port `3979:3979`, env `BOT_ENDPOINT: http://echo-bot:3978/api/messages`,
`SERVICE_URL: http://fake-teams:3979`. Wire **container-to-container on `locadev`** - no
`host.docker.internal` for bot traffic, no overlay compose file.

It must present the same control plane real Teams does, so a bot built here behaves identically on real
Teams. Every inbound activity carries `channelId: "msteams"`, `channelData.tenant.id`, `serviceUrl`,
`from`, `recipient`, and a `conversation` object with `conversationType`/`isGroup`.

Inbound (channel to bot) test hooks:

| Path | Activity produced |
|---|---|
| `POST /api/inject` | `message` - the main "user said something" hook |
| `POST /api/conversation-update` | `conversationUpdate` with `membersAdded`/`membersRemoved` - drives welcome flows |
| `POST /api/reaction` | `messageReaction` with `reactionsAdded`/`reactionsRemoved` |
| `POST /api/invoke` | `invoke` - Adaptive Card `Action.Execute`, `task/fetch|submit`, compose extensions |

**Invoke is synchronous:** the bot answers with an `InvokeResponse` **in the HTTP response body**, not
via `serviceUrl`. Capture that response and store it as an `invokeResponse` activity.

Connector REST (bot to channel, on `serviceUrl`) - the surface the Bot Framework SDK calls:
`POST /v3/conversations/{id}/activities`, `POST|PUT|DELETE /v3/conversations/{id}/activities/{activityId}`,
`GET /v3/conversations/{id}/members`, `GET /v3/conversations/{id}/pagedmembers`, `POST /v3/conversations`.

Read/admin: `GET /health`, `GET /api/messages?conversation_id&direction&since` (returns `next_since` for
cursor polling; `direction` filters `user`/`bot`/`event`), `GET /api/transcript`, `GET /api/members`,
`POST /api/reset`.

Out of scope, state it: JWT/auth, real AAD, SharePoint-backed rosters, message-extension UI.

`echo-bot`: build `./echo_bot`, port `3978:3978`, env
`BRIDGE_ENDPOINT: ${ECHO_BOT_BRAIN-http://bridge:8090}` and `TOPAZ_ENDPOINT: http://topaz:8383`,
`depends_on: [bridge, topaz]`.
- Written like a real `TeamsActivityHandler` so the control-plane paths get exercised: welcome on
  `membersAdded` (never welcome the bot itself), echo/answer on `message`, ack `messageReaction`, inline
  `InvokeResponse` on `invoke`, ack everything else.
- Brain: default is the **sandbox bridge** by service name, so answer quality tracks `CHAT_BACKEND`.
  Setting `ECHO_BOT_BRAIN=` (empty) selects the plain echo brain - required for the echo assertions in
  `tests/teams/`. On a bridge error, fall back to an echo prefixed with the specific error type.
- **HITL approvals are authz-gated:** an `invoke` whose `value.verb` is `approve`/`reject` with a `user`
  first calls Topaz with `policy_context.path = "approval"`. Allowed returns status 200 and posts a
  confirmation to the conversation; denied returns **403** and posts a refusal. Fail closed.

Note the `claude-cli` caveat: that brain is host-only, so the Claude-brain path runs host-side;
`fake` and `ollama` work fully dockerized.

`mcp_server/` + `.mcp.json`: a **host-run** MCP server (`mcp>=1.2.0`, `httpx`) exposing the channel as
tools - `teams_send`, `teams_read`, `teams_replies`, `teams_transcript`, `teams_join`, `teams_invoke`,
`teams_members`, `teams_reset` - over `FAKE_TEAMS_BASE=http://localhost:3979`. Register it in a
**repo-local** `.mcp.json` with an explicit comment that it is for this repo only and must not be
copied into a wider workspace config.

### `sample` - in-repo sample consumer service
Build `./sample_service` (FastAPI), port `18080:8080`, wired to `pglite` / `redis` / `bridge` **by
service name**. Env points at local equivalents only — no sibling private repos, no build-time patches
of external codebases.

Example env:
- `PGLITE_URL: http://pglite:5433`
- `REDIS_URL: redis://redis:6379`
- `AZURE_OPENAI_ENDPOINT: http://bridge:8090/`
- throwaway API key, chat deployment name, api version

This profile exists so `locadev` can prove end-to-end wiring without cloning another product repo.

---

## 9. Phase 6 - `sandbox.env.example`, the consumer contract

This file is the product. It lists every value a client repo needs, with a header stating: copy only
the vars **your** repo uses; names differ per repo (C# `appsettings` `"Section:Key"` vs Python
`UPPER_SNAKE`) but **the values are what matter**; run the client on the same host as Docker Desktop
(or Linux Engine); moving to a real cloud sandbox later is a value swap with no code change.

Sections and the load-bearing values:
- **Azurite** - the **full** connection string with `DefaultEndpointsProtocol=http`,
  `AccountName=devstoreaccount1`, the well-known dev `AccountKey`, and explicit
  `BlobEndpoint`/`QueueEndpoint`/`TableEndpoint` on `127.0.0.1:10000/10101/10002`.
  **Gotcha:** Python's `azure-storage-blob` needs this full string; the .NET
  `UseDevelopmentStorage=true` shorthand does not work for it.
- **Service Bus** - `Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;`
  and a comment naming the declared entities (`app-work-queue`, `dev-ingestion-queue`, `emailrequest`,
  `app-events`).
- **Azure OpenAI** - endpoint `http://127.0.0.1:8090`, any key, `2025-01-01-preview`; note the key is
  ignored and deployment names pass through.
- **PGlite (app SQL)** - `http://127.0.0.1:5433` for the HTTP API; if PG-wire is enabled,
  `postgresql://locadev:locadev@127.0.0.1:5432/locadev`. State that this is **not** the Service Bus
  internal MSSQL.
- **Cosmos** (HTTP `:8081` + the public emulator key), **AWS S3** (`AWS_ENDPOINT_URL`,
  `test`/`test`, `us-east-1`), **Key Vault** (`USE_KEY_VAULT=false` default), **Topaz** (`:8484`),
  **Redis** (`127.0.0.1:6380` from host, `redis:6379` from containers).

Do **not** document a separate published app SQL Server. App relational data goes through PGlite.

---

## 10. Phase 7 - tests and demos

Two distinct layers. Keep them separate.

**`tests/` - bare connectivity smoke, no Topaz.** One file per service: blob, servicebus, bridge,
pglite, cosmos, s3, mail (profile), aisearch (profile). Each test **skips** when its service is not up
rather than failing (use a `port_open` helper in `conftest.py` that also holds the shared connection
constants). The bridge test drives `openai.AzureOpenAI` - the real client. The pglite test hits
`POST /sql` with a trivial `select 1` and checks vector extension if seed ran. Pinned requirements that
matter:
```
pytest==8.3.4
azure-storage-blob==12.24.0
azure-servicebus==7.14.3      # >=7.13 REQUIRED for the emulator's AMQP; 7.12.3 times out
openai==1.59.6
httpx==0.28.1                 # PGlite HTTP + mail + aisearch
azure-cosmos==4.9.0
boto3==1.35.99
```
Do **not** require `pymssql` or a host ODBC driver for app SQL — app SQL is PGlite over HTTP (or optional
wire via `psycopg` only if that gateway ships).

**`demos/` - Topaz-gated app patterns.** Each demo mirrors a common cloud code path and calls
`require(user, action)` before acting, so the stack demonstrates policy-controlled access in front of
every service:

| Demo | Mirrors | Actions |
|---|---|---|
| `blob_artifacts.py` | Blob SDK upload/download | write=editor, read=editor+viewer |
| `servicebus_events.py` | publish/consume on `app-events` | publish=editor, consume=editor+viewer |
| `pglite_notes.py` | app SQL via PGlite HTTP + optional vector insert | write=editor, read=editor+viewer |
| `cosmos_chat_history.py` | document chat history | write=editor, read=editor+viewer |
| `foundry_chat_embed.py` | Azure OpenAI chat + 1536-dim embeddings | both require `infer` |
| `s3_objects.py` | S3 list/get against MiniStack seed keys | read=crawl |

The demos must prove the policy: `alice@example.com` (editor) allowed, `bob@example.com` (viewer)
denied on writes.

**`tests/teams/`** covers the Teams profile; start that stack with `ECHO_BOT_BRAIN=` so the echo
assertions hold.

Run tests on the **Docker host** (macOS or Linux), from a project-local venv (not a machine-global
path that other projects share):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip -q install -r tests/requirements.txt
pytest -q tests
# with teams profile up and ECHO_BOT_BRAIN empty:
pytest -q tests/teams
```

**Gate 4.** Core smoke tests pass against `docker compose up -d --build`. Profile tests skip cleanly
when their profile is off.

---

## 11. Phase 8 - README contract

`README.md` must include, in this order:

1. **One-paragraph pitch** — local Azure/AWS surface for env-only client config; interim, not full cloud fidelity.
2. **Honest limitations** — Topaz ≠ Entra RBAC; AI Search filter/rerank approximations; PGlite ≠ multi-tenant server Postgres; SB MSSQL is internal-only.
3. **Prerequisites** — Docker Desktop on Mac / Engine on Linux; optional Ollama / Claude CLI.
4. **Quick start** — `cp .env.example .env` → `make up` or `./scripts/start.sh` → `make verify` → paste from `sandbox.env.example`.
5. **Port table** — same as section 3 (or link to it).
6. **Profiles** — what each profile adds and when to enable it.
7. **Consumer contract** — point hard at `sandbox.env.example`.
8. **Backend selection** — `fake` / `ollama` / `claude-cli` for the bridge.
9. **Mac notes** — host Ollama via `host.docker.internal`; no WSL requirement; Docker Desktop resource tips for Cosmos.
10. **Troubleshooting** — SB Config.json `Logging` sibling gotcha; Azurite full connection string; Service Bus SDK version; PGlite single-connection expectations.

Tone: practical, no marketing. Prefer "what breaks and how to fix it" over feature lists.

---

## 12. Implementation order and acceptance

Build in this order; do not skip gates.

| Gate | Check |
|---|---|
| 1 | Core seven services up; SB health, bridge health, PGlite health answer |
| 2 | `bridge/harness.py` chat + 1536 embedding |
| 3 | `scripts/verify.sh` → `Core services OK.` |
| 4 | `pytest tests` green for core; profile tests skip when off |
| 5 | At least one Topaz demo proves alice allowed / bob denied on write |
| 6 | `sandbox.env.example` + README match running ports and names |

**Done means:** a developer on a Mac can clone `locadev`, run `make up && make verify`, point a client
repo at `sandbox.env.example` values, and exercise blob / bus / OpenAI / app SQL (PGlite) without a
cloud subscription and without editing client code.

---

## 13. Explicit non-goals (keep the repo focused)

- Not a real Azure subscription, Entra tenant, or managed identity.
- Not Windows-first; no required PowerShell or WSL path.
- Not a vendor-specific product monorepo (no AECOM/RW/FA naming, queues, or seed trees).
- Not shipping a full multi-writer Postgres server by default — **PGlite** is the app DB.
- Not requiring a separate published SQL Server for app data.
- Not building external sibling apps inside this compose file.

---

## 14. Optional later (do not block v1)

- PG-wire gateway in front of PGlite if enough clients demand `psycopg`/`Npgsql` without HTTP.
- Full `postgres:16` + pgvector profile for heavy concurrency testing.
- Windows helpers that shell out to the same bash scripts (never probe ports from a flaky host path).
- Extra AWS services on MiniStack when a consumer flow needs them.
