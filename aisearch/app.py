"""Azure AI Search emulator backed by Qdrant.

Approximation notes (honesty rule):
- No real L2 semantic reranker; @search.rerankerScore echoes hybrid score.
- $filter only supports simple field eq 'value' AND conjunctions; complex
  filters are ignored, logged, and echoed as emulator notes.
- Hybrid RRF approximated by letting vector ANN dominate.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any
from uuid import UUID, uuid5

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

logger = logging.getLogger("aisearch")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="locadev-aisearch")

QDRANT_URL = __import__("os").environ.get("QDRANT_URL", "http://qdrant:6333")
FIXED_NS = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
_KEY = "_locadev_key"
_TEXT = "_locadev_text"

# index_name -> metadata
_indexes: dict[str, dict[str, Any]] = {}


def client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, prefer_grpc=False)


def point_id(index: str, key: str) -> str:
    return str(uuid5(FIXED_NS, f"{index}:{key}"))


def parse_odata_name(path: str) -> list[tuple[str, str | None]]:
    """Parse Azure OData-style path segments: indexes('foo')/docs('bar')."""
    segments: list[tuple[str, str | None]] = []
    # also accept slash forms indexes/foo/docs/bar
    remaining = path.strip("/")
    while remaining:
        m = re.match(r"^([a-zA-Z0-9_.-]+)(?:\('([^']*)'\))?/?", remaining)
        if not m:
            slash = remaining.split("/", 1)
            segments.append((slash[0], None))
            remaining = slash[1] if len(slash) > 1 else ""
            continue
        segments.append((m.group(1), m.group(2)))
        remaining = remaining[m.end() :]
    return segments


@app.get("/health")
def health() -> dict[str, Any]:
    qdrant_ok = False
    try:
        client().get_collections()
        qdrant_ok = True
    except Exception as e:
        logger.warning("qdrant unreachable: %s", e)
    return {
        "status": "ok" if qdrant_ok else "degraded",
        "indexes": list(_indexes.keys()),
        "qdrant": qdrant_ok,
    }


def _parse_index_meta(schema: dict[str, Any]) -> dict[str, Any]:
    fields = schema.get("fields") or []
    key_field = "id"
    vec_name = None
    dim = 1
    metric = "Cosine"
    searchable: list[str] = []
    for f in fields:
        name = f.get("name") or ""
        if f.get("key"):
            key_field = name or key_field
        t = f.get("type") or ""
        if "Collection(Edm.Single)" in t or "Collection(Edm.Half)" in t:
            vec_name = name
            dims = f.get("dimensions")
            if dims:
                dim = int(dims)
        if f.get("searchable") and t in ("Edm.String",):
            searchable.append(name)
    vs = schema.get("vectorSearch") or {}
    for alg in vs.get("algorithms") or []:
        params = alg.get("hnswParameters") or {}
        m = (params.get("metric") or "cosine").lower()
        if m in ("euclidean", "l2"):
            metric = "Euclid"
        elif m in ("dotproduct", "dot"):
            metric = "Dot"
        else:
            metric = "Cosine"
    if not vec_name:
        dim = 1
        metric = "Cosine"
    return {
        "name": schema.get("name"),
        "key_field": key_field,
        "vector_field": vec_name,
        "dim": dim,
        "metric": metric,
        "searchable": searchable,
        "schema": schema,
    }


def _ensure_collection(meta: dict[str, Any]) -> None:
    name = meta["name"]
    distance = {
        "Cosine": qm.Distance.COSINE,
        "Euclid": qm.Distance.EUCLID,
        "Dot": qm.Distance.DOT,
    }.get(meta["metric"], qm.Distance.COSINE)
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if name in existing:
        c.delete_collection(name)
    c.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=meta["dim"], distance=distance),
    )


@app.post("/indexes")
async def create_index(request: Request) -> Any:
    schema = await request.json()
    name = schema.get("name")
    if not name:
        return JSONResponse(status_code=400, content={"error": "name required"})
    meta = _parse_index_meta(schema)
    meta["name"] = name
    _ensure_collection(meta)
    _indexes[name] = meta
    return schema


async def _handle_index_crud(name: str, method: str, request: Request) -> Any:
    if method == "GET":
        if name not in _indexes:
            return JSONResponse(status_code=404, content={"error": "not found"})
        return _indexes[name]["schema"]
    if method == "DELETE":
        if name in _indexes:
            try:
                client().delete_collection(name)
            except Exception:
                pass
            del _indexes[name]
        return ResponseNoContent()
    if method in ("PUT", "POST"):
        schema = await request.json()
        schema["name"] = name
        meta = _parse_index_meta(schema)
        meta["name"] = name
        _ensure_collection(meta)
        _indexes[name] = meta
        return schema
    return JSONResponse(status_code=405, content={"error": "method not allowed"})


class ResponseNoContent(JSONResponse):
    def __init__(self) -> None:
        super().__init__(content=None, status_code=204)


def _simple_filters(filter_expr: str | None) -> tuple[qm.Filter | None, list[str]]:
    notes: list[str] = []
    if not filter_expr or not filter_expr.strip():
        return None, notes
    # only field eq 'value' joined by and
    parts = re.split(r"\s+and\s+", filter_expr, flags=re.I)
    must: list[qm.FieldCondition] = []
    complex_pat = re.compile(r"\bor\b|\bnot\b|[<>]|search\.ismatch|\(", re.I)
    if complex_pat.search(filter_expr):
        msg = f"complex $filter ignored (partial OData): {filter_expr}"
        logger.warning(msg)
        notes.append(msg)
        return None, notes
    for part in parts:
        m = re.match(r"^\s*([a-zA-Z0-9_]+)\s+eq\s+'([^']*)'\s*$", part, re.I)
        if not m:
            msg = f"unsupported filter clause ignored: {part}"
            logger.warning(msg)
            notes.append(msg)
            continue
        must.append(
            qm.FieldCondition(key=m.group(1), match=qm.MatchValue(value=m.group(2)))
        )
    if not must:
        return None, notes
    return qm.Filter(must=must), notes


async def _index_docs(name: str, body: dict[str, Any]) -> Any:
    if name not in _indexes:
        return JSONResponse(status_code=404, content={"error": f"index {name} not found"})
    meta = _indexes[name]
    c = client()
    results = []
    batch_failed = False
    for doc in body.get("value") or []:
        action = doc.get("@search.action", "upload")
        key = str(doc.get(meta["key_field"], doc.get("id", "")))
        pid = point_id(name, key)
        try:
            if action == "delete":
                c.delete(collection_name=name, points_selector=[pid])
                results.append(
                    {"key": key, "status": True, "errorMessage": None, "statusCode": 200}
                )
                continue

            existing = None
            if action in ("merge", "mergeOrUpload"):
                try:
                    pts = c.retrieve(collection_name=name, ids=[pid], with_vectors=True)
                    existing = pts[0] if pts else None
                except Exception:
                    existing = None
                if action == "merge" and existing is None:
                    results.append(
                        {
                            "key": key,
                            "status": False,
                            "errorMessage": "Document not found",
                            "statusCode": 404,
                        }
                    )
                    batch_failed = True
                    continue

            payload = {k: v for k, v in doc.items() if not k.startswith("@")}
            payload[_KEY] = key
            # stash searchable text
            texts = [str(payload.get(f, "")) for f in meta["searchable"]]
            payload[_TEXT] = " ".join(texts)

            vec = None
            vf = meta["vector_field"]
            if vf and vf in doc and doc[vf] is not None:
                vec = list(doc[vf])
                if len(vec) < meta["dim"]:
                    vec = vec + [0.0] * (meta["dim"] - len(vec))
                elif len(vec) > meta["dim"]:
                    vec = vec[: meta["dim"]]
            elif existing is not None and action == "merge":
                vec = existing.vector
                if isinstance(vec, dict):
                    vec = next(iter(vec.values()), None)
                # merge payloads
                old = dict(existing.payload or {})
                old.update(payload)
                payload = old
            else:
                vec = [0.0] * meta["dim"]

            c.upsert(
                collection_name=name,
                points=[qm.PointStruct(id=pid, vector=vec, payload=payload)],
            )
            results.append(
                {"key": key, "status": True, "errorMessage": None, "statusCode": 200}
            )
        except Exception as e:
            batch_failed = True
            results.append(
                {
                    "key": key,
                    "status": False,
                    "errorMessage": str(e),
                    "statusCode": 400,
                }
            )
    status = 207 if batch_failed else 200
    return JSONResponse(status_code=status, content={"value": results})


async def _search(name: str, body: dict[str, Any]) -> Any:
    if name not in _indexes:
        return JSONResponse(status_code=404, content={"error": f"index {name} not found"})
    meta = _indexes[name]
    c = client()
    top = int(body.get("top") or 50)
    select = body.get("select")
    select_fields = (
        [s.strip() for s in select.split(",")] if isinstance(select, str) else None
    )
    query_type = body.get("queryType") or "simple"
    search_text = body.get("search") or ""
    filt, notes = _simple_filters(body.get("filter") or body.get("$filter"))

    vector = None
    k = top
    for vq in body.get("vectorQueries") or []:
        if vq.get("kind") == "vector" and vq.get("vector"):
            vector = list(vq["vector"])
            if len(vector) < meta["dim"]:
                vector = vector + [0.0] * (meta["dim"] - len(vector))
            elif len(vector) > meta["dim"]:
                vector = vector[: meta["dim"]]
            k = int(vq.get("k") or top)
            break

    hits: list[dict[str, Any]] = []
    if vector is not None:
        res = c.search(
            collection_name=name,
            query_vector=vector,
            limit=k,
            query_filter=filt,
            with_payload=True,
        )
        for p in res:
            score = float(p.score or 0)
            doc = dict(p.payload or {})
            key = doc.pop(_KEY, None)
            doc.pop(_TEXT, None)
            if meta["key_field"] not in doc and key:
                doc[meta["key_field"]] = key
            if select_fields:
                doc = {f: doc.get(f) for f in select_fields if f in doc or f == meta["key_field"]}
            item = {**doc, "@search.score": score}
            if query_type == "semantic":
                item["@search.rerankerScore"] = score  # approximation
            hits.append(item)
    else:
        # text scroll with naive token score
        points, _ = c.scroll(
            collection_name=name,
            scroll_filter=filt,
            limit=1000,
            with_payload=True,
        )
        tokens = []
        if search_text and search_text.strip() != "*":
            tokens = [t.lower() for t in re.findall(r"\w+", search_text)]
        scored = []
        for p in points:
            payload = dict(p.payload or {})
            text = (payload.get(_TEXT) or "").lower()
            if tokens:
                score = float(sum(1 for t in tokens if t in text))
                if score <= 0:
                    continue
            else:
                score = 1.0
            scored.append((score, payload))
        scored.sort(key=lambda x: -x[0])
        for score, payload in scored[:top]:
            key = payload.pop(_KEY, None)
            payload.pop(_TEXT, None)
            if meta["key_field"] not in payload and key:
                payload[meta["key_field"]] = key
            if select_fields:
                payload = {
                    f: payload.get(f)
                    for f in select_fields
                    if f in payload or f == meta["key_field"]
                }
            item = {**payload, "@search.score": score}
            if query_type == "semantic":
                item["@search.rerankerScore"] = score
            hits.append(item)

    out: dict[str, Any] = {"value": hits, "@odata.count": len(hits)}
    if notes:
        out["@locadev.emulatorNotes"] = notes
    return out


async def _get_doc(name: str, key: str) -> Any:
    if name not in _indexes:
        return JSONResponse(status_code=404, content={"error": "index not found"})
    pid = point_id(name, key)
    pts = client().retrieve(collection_name=name, ids=[pid], with_payload=True)
    if not pts:
        return JSONResponse(status_code=404, content={"error": "not found"})
    doc = dict(pts[0].payload or {})
    doc.pop(_TEXT, None)
    doc.pop(_KEY, None)
    return doc


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dispatcher(full_path: str, request: Request) -> Any:
    """Catch-all for OData and slash-style Azure AI Search paths."""
    # strip query handled by FastAPI
    path = full_path
    method = request.method.upper()
    segments = parse_odata_name(path)

    # indexes
    if not segments:
        return JSONResponse(status_code=404, content={"error": "not found"})

    if segments[0][0] == "indexes":
        if len(segments) == 1 and segments[0][1] is None and method == "POST":
            return await create_index(request)
        # indexes('name') or indexes/name
        if len(segments) >= 1:
            name = segments[0][1]
            idx = 1
            if name is None and len(segments) >= 2:
                name = segments[1][0]
                idx = 2
            elif name is None:
                return JSONResponse(status_code=400, content={"error": "index name required"})
            else:
                idx = 1

            rest = segments[idx:]
            if not rest:
                return await _handle_index_crud(name, method, request)

            # docs...
            if rest[0][0] in ("docs", "docs.search.index", "docs.search.post.search"):
                action = rest[0][0]
                doc_key = rest[0][1]
                if len(rest) == 1 and doc_key and method == "GET":
                    return await _get_doc(name, doc_key)
                if action == "docs" and len(rest) == 1 and method == "GET":
                    # simple GET query ?search=
                    q = request.query_params.get("search", "*")
                    return await _search(name, {"search": q, "top": 50})
                if len(rest) >= 2:
                    sub = rest[1][0]
                    if sub in ("search.index", "index") and method == "POST":
                        body = await request.json()
                        return await _index_docs(name, body)
                    if sub in ("search.post.search", "search") and method == "POST":
                        body = await request.json()
                        return await _search(name, body)
                # docs/search.index as single weird segment
                if "search.index" in action or action.endswith("index"):
                    body = await request.json()
                    return await _index_docs(name, body)
                if "search" in action:
                    body = await request.json()
                    return await _search(name, body)

            # slash forms: docs/index, docs/search
            if rest[0][0] == "docs" and len(rest) >= 2:
                sub = rest[1][0]
                if sub == "index" and method == "POST":
                    return await _index_docs(name, await request.json())
                if sub == "search" and method == "POST":
                    return await _search(name, await request.json())

    return JSONResponse(
        status_code=404, content={"error": f"unhandled path /{full_path}"}
    )
