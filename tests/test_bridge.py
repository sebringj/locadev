from openai import AzureOpenAI

from conftest import BRIDGE, require_port


def test_bridge_chat_and_embeddings():
    require_port(8090, "Bridge")
    client = AzureOpenAI(
        azure_endpoint=BRIDGE,
        api_key="not-used",
        api_version="2025-01-01-preview",
    )
    chat = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "smoke test"}],
    )
    assert chat.choices[0].message.content
    emb = client.embeddings.create(
        model="text-embedding-ada-002",
        input="smoke embedding",
    )
    assert len(emb.data[0].embedding) == 1536
