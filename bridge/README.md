# Foundry bridge

Azure OpenAI URL shape → `fake` | `ollama` | `claude-cli`.

- Chat: `POST /openai/deployments/{name}/chat/completions`
- Embeddings: `POST /openai/deployments/{name}/embeddings`
- Health: `GET /health`

API key ignored; `api-version` any value; deployment names pass through.
