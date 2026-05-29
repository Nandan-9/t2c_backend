import mimetypes
import uuid

import boto3
from botocore.client import Config
from django.conf import settings

_MAX_SIZE = {
    "image": 5 * 1024 * 1024,    # 5 MB
    "video": 100 * 1024 * 1024,  # 100 MB (~720p 1 min)
}
_FOLDER = {"image": "posts/images", "video": "posts/videos"}
_DEFAULT_CONTENT_TYPE = {"image": "image/jpeg", "video": "video/mp4"}
_DEFAULT_EXT = {"image": "jpg", "video": "mp4"}

PRESIGNED_URL_EXPIRY = 600  # 10 minutes


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION,
        endpoint_url=f"https://s3.{settings.AWS_S3_REGION}.amazonaws.com",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )


def generate_upload_url(media_type: str, content_type: str | None = None) -> dict:
    if content_type is None:
        content_type = _DEFAULT_CONTENT_TYPE[media_type]

    ext = mimetypes.guess_extension(content_type)
    # mimetypes can return None or platform-specific aliases (e.g. .jpe, .jpeg)
    if ext is None:
        ext = _DEFAULT_EXT[media_type]
    else:
        ext = ext.lstrip(".")
        # normalize common jpeg aliases
        if ext in ("jpe", "jpeg"):
            ext = "jpg"

    key = f"{_FOLDER[media_type]}/{uuid.uuid4()}.{ext}"
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
        "max_size_bytes": _MAX_SIZE[media_type],
        "content_type": content_type,
    }


def get_public_url(key: str) -> str:
    bucket = settings.AWS_S3_BUCKET_NAME
    region = settings.AWS_S3_REGION
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
