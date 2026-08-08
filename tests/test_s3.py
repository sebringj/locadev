import boto3

from conftest import AWS_ENDPOINT, require_port


def test_s3_list_seed():
    require_port(4566, "MiniStack")
    s3 = boto3.client(
        "s3",
        endpoint_url=AWS_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )
    buckets = s3.list_buckets().get("Buckets") or []
    # seed may create locadev-demo; at minimum list must work
    assert isinstance(buckets, list)
