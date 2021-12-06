from urllib.parse import unquote_plus
import boto3

client = boto3.client("rekognition")


class PhotoDoesNotMeetRequirementError(Exception):
    pass


def handler(event, context):
    bucket = event["bucket"]
    key = unquote_plus(event["key"])

    # Detect the faces
    try:
        response = client.detect_faces(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            Attributes=[
                "ALL",
            ],
        )
    except client.exceptions.ImageTooLargeException as e:
        raise PhotoDoesNotMeetRequirementError(f"{e}")
    except client.exceptions.InvalidImageFormatException:
        raise PhotoDoesNotMeetRequirementError(
            "Unsupported image file format. Only JPEG or PNG is supported."
        )
    else:
        if not response["FaceDetails"]:
            raise PhotoDoesNotMeetRequirementError("No face detected on the photo.")
        elif len(response["FaceDetails"]) > 1:
            raise PhotoDoesNotMeetRequirementError(
                "Detected more than one face in the photo."
            )
        else:
            face_detail = response["FaceDetails"][0]
            face_detail.pop("Landmarks")

            return face_detail
