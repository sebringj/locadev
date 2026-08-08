from azure.storage.blob import BlobServiceClient

from conftest import AZURITE_CONN, require_port


def test_blob_upload_download():
    require_port(10000, "Azurite")
    client = BlobServiceClient.from_connection_string(AZURITE_CONN)
    container = client.get_container_client("locadev-smoke")
    try:
        container.create_container()
    except Exception:
        pass
    data = b"hello-locadev"
    container.upload_blob("smoke.txt", data, overwrite=True)
    got = container.download_blob("smoke.txt").readall()
    assert got == data
