from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.services.media_service import generate_upload_url

VALID_MEDIA_TYPES = ("image", "video")


class MediaUploadUrlView(APIView):
    """
    POST /posts/media/upload-url/
    Body: { "media_type": "image" | "video", "content_type": "image/png" }
    content_type is optional; defaults to image/jpeg or video/mp4.
    Returns a presigned S3 PUT URL valid for 10 minutes.
    The frontend uploads the file directly to S3, then passes the returned
    key in the post-creation request.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        media_type = request.data.get("media_type")
        if media_type not in VALID_MEDIA_TYPES:
            return Response(
                {"error": "media_type must be 'image' or 'video'"},
                status=400,
            )

        content_type = request.data.get("content_type")
        if content_type is not None:
            expected_prefix = f"{media_type}/"
            if not content_type.startswith(expected_prefix):
                return Response(
                    {"error": f"content_type must start with '{expected_prefix}'"},
                    status=400,
                )

        return Response(generate_upload_url(media_type, content_type), status=200)
