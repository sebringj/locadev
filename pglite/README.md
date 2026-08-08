# PGlite (app database)

WASM Postgres with **pgvector**, exposed over HTTP for locadev demos and smoke tests.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | `{status, backend: "pglite", extensions: ["vector"]}` |
| POST | `/sql` | `{ "sql", "params" }` → `{ rows, fields, rowCount }` |
| POST | `/exec` | multi-statement script |
| GET | `/ready` | 200 after seed |

Host: `http://127.0.0.1:5433` · containers: `http://pglite:5433`

## Limitations

- Single-connection spirit — not a multi-writer server Postgres.
- This is **app** data only. Service Bus MSSQL is separate and unpublished.
- Optional PG-wire gateway is not shipped in v1.
