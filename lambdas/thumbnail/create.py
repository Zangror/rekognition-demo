import os
import uuid

from urllib.parse import unquote_plus

import boto3
from PIL import Image

s3_client = boto3.client("s3")

BUCKET_THUMBNAIL = os.environ["BUCKET"]


def handler(event, context):
    bucket = event["bucket"]
    key = unquote_plus(event["key"])

    tmp_key = key.replace("/", "")
    download_path = f"/tmp/{uuid.uuid4()}{tmp_key}"
    upload_path = f"/tmp/resized-{tmp_key}"

    # Download
    s3_client.download_file(bucket, key, download_path)

    # Resize
    with Image.open(download_path) as image:
        image.thumbnail(tuple(x / 2 for x in image.size))
        image.save(upload_path)

    # Write it back to S3
    s3_client.upload_file(upload_path, BUCKET_THUMBNAIL, key)

    return {
        "bucket": BUCKET_THUMBNAIL,
        "key": key,
    }
