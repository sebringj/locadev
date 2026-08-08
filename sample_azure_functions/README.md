# Azure Functions + Azurite (locadev)

Azurite is **core** in locadev. This profile adds a **Functions-style runtime sample**
that uses Azurite for queue I/O the same way real Functions use `AzureWebJobsStorage`.

## Why not the official Functions Docker image?

Microsoft’s `azure-functions/*` images are **linux/amd64** and currently **crash under QEMU**
on Apple Silicon. Core Tools also lacks a reliable **linux-arm64** CLI package in Docker.

So locadev ships:

1. **Profile `functions`** — multi-arch Node worker (`server.mjs`) + Azurite queues (works on Mac ARM).
2. **Host Core Tools path** — run the real Functions host on your machine against the same Azurite
   (`src/index.js` + `@azure/functions` v4 programming model).

## Profile (Docker)

```bash
docker compose -p locadev --profile functions up -d --build
# or: ./scripts/start.sh functions
```

| Endpoint | Purpose |
|----------|---------|
| `GET http://127.0.0.1:7071/api/ping` | Host up |
| `GET http://127.0.0.1:7071/api/httpHello?name=world` | Enqueue to Azurite queue `functions-work` |
| `GET http://127.0.0.1:7071/api/processed` | Messages the worker drained (see queue path) |
| `GET http://127.0.0.1:7071/health` | Health + queue status |

Compose wires storage to **in-network** Azurite:

```text
BlobEndpoint=http://azurite:10000/...
QueueEndpoint=http://azurite:10001/...
TableEndpoint=http://azurite:10002/...
```

## Real Functions host on your machine (`func start`)

```bash
# locadev core (Azurite) already up
export AzureWebJobsStorage='DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10101/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;'
export FUNCTIONS_WORKER_RUNTIME=node
export AzureWebJobsFeatureFlags=EnableWorkerIndexing

cd sample_azure_functions
npm install
# requires Azure Functions Core Tools on the host:
func start --javascript
```

**Host ports:** blob `10000`, queue **`10101`** (mapped from container 10001), table `10002`.  
See `sandbox.env.example` → `AzureWebJobsStorage`.

## Honesty

| Layer | What you get |
|-------|----------------|
| Azurite | Real local Azure Storage API for bindings |
| Profile `functions` | Functions-**style** HTTP + queue loop (great for CI/Mac) |
| Host `func start` | Full Microsoft Functions host when Core Tools is installed |

Not included: consumption plan, portal, managed identity, Durable-at-scale.
