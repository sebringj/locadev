"""Host-side connection constants for locadev core services."""

from __future__ import annotations

import os

AZURITE_CONN = os.environ.get(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10101/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;",
)
SERVICEBUS_CONN = os.environ.get(
    "SERVICEBUS_CONNECTION_STRING",
    "Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;"
    "SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;",
)
BRIDGE = os.environ.get("AZURE_OPENAI_ENDPOINT", "http://127.0.0.1:8090").rstrip("/")
PGLITE = os.environ.get("PGLITE_HTTP_URL", "http://127.0.0.1:5433").rstrip("/")
TOPAZ = os.environ.get("TOPAZ_URL", "http://127.0.0.1:8484").rstrip("/")
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380")
CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1")
EMBED_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-ada-002")
BLOB_CONTAINER = "locadev-playground"
SB_QUEUE = "app-work-queue"
