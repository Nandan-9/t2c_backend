from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from users.serializers import UserSerializer
from users.services.user_services import get_avatar_upload_url, get_public_url

User = get_user_model()


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class UsernameCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        username = request.query_params.get("username", "").strip()
        if not username:
            return Response({"detail": "username query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        available = not User.objects.filter(username__iexact=username).exists()
        return Response({"available": available})





class AvatarUploadUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.data.get("content_type")
        result = get_avatar_upload_url(content_type)
        return Response(result)


class EditProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        key = request.data.get("key")
        if not key:
            return Response({"message": "key is required"}, status=status.HTTP_400_BAD_REQUEST)
        public_url = get_public_url(key)
        print(public_url)
        request.user.avatar_url = public_url
        request.user.save(update_fields=["avatar_url"])
        return Response({"avatar_url": public_url})
