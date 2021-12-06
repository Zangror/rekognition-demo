import os

from urllib.parse import unquote_plus
import boto3

client = boto3.client("rekognition")

COLLECTION_ID = os.environ["REKOGNITION_COLLECTION_ID"]


def handler(event, context):
    bucket = event["bucket"]
    key = unquote_plus(event["key"])
    user_id = event["user_id"]

    # Detect the faces
    response = client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        DetectionAttributes=["ALL"],
        MaxFaces=1,
        ExternalImageId=user_id,
    )

    return response["FaceRecords"][0]["Face"]
