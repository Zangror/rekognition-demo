import os

from urllib.parse import unquote_plus
import boto3

client = boto3.client("rekognition")

COLLECTION_ID = os.environ["REKOGNITION_COLLECTION_ID"]


def handler(event, context):
    bucket = event["bucket"]
    key = unquote_plus(event["key"])

    # Detect the faces
    response = client.search_faces_by_image(
        CollectionId=COLLECTION_ID,
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxFaces=1,
        FaceMatchThreshold=90.0,
    )

    if not response["FaceMatches"]:
        return {"exists": False}
    else:
        return {
            "exists": True,
            "user_id": response["FaceMatches"][0]["Face"]["ExternalImageId"],
        }
