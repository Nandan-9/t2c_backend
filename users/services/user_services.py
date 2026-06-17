import mimetypes
import uuid

import boto3
from botocore.client import Config
from django.conf import settings
from rest_framework.exceptions import ValidationError

PRESIGNED_URL_EXPIRY = 600


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION,
        endpoint_url=f"https://s3.{settings.AWS_S3_REGION}.amazonaws.com",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def get_avatar_upload_url(content_type):
    if not content_type:
        raise ValidationError({"message": "content_type is required"})

    if not content_type.startswith("image/"):
        raise ValidationError({"message": "content_type must be an image type"})

    ext = mimetypes.guess_extension(content_type)
    if ext is None:
        ext = "jpg"
    else:
        ext = ext.lstrip(".")
        if ext in ("jpe", "jpeg"):
            ext = "jpg"

    key = f"users/avatars/{uuid.uuid4()}.{ext}"
    upload_url = _s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRY,
    )

    return {
        "upload_url": upload_url,
        "key": key,
        "expires_in": PRESIGNED_URL_EXPIRY,
        "content_type": content_type,
    }


def get_public_url(key: str) -> str:
    bucket = settings.AWS_S3_BUCKET_NAME
    region = settings.AWS_S3_REGION
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
