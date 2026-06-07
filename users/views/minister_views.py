from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import MinisterFollowSerializer, MinisterSerializer
from users.services import minister_service


class MinisterListCreateView(APIView):
    """
    GET  /users/ministers/         — list all ministers (any authenticated user)
    POST /users/ministers/         — create a minister (admin only)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUser()]
        return [AllowAny()]

    def get(self, request):
        ministers = minister_service.get_all_ministers()
        data = MinisterSerializer(ministers, many=True).data
        return Response(data)

    def post(self, request):
        serializer = MinisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            minister = minister_service.create_minister(serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MinisterSerializer(minister).data, status=status.HTTP_201_CREATED)


class MinisterDetailView(APIView):
    """
    GET    /users/ministers/<id>/   — retrieve a minister (any authenticated user)
    PATCH  /users/ministers/<id>/   — edit a minister (admin only)
    DELETE /users/ministers/<id>/   — delete a minister (admin only)
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [IsAdminUser()]
        return [AllowAny()]

    def _get_minister_or_404(self, minister_id):
        minister = minister_service.get_minister_by_id(minister_id)
        if not minister:
            return None, Response({"detail": "Minister not found."}, status=status.HTTP_404_NOT_FOUND)
        return minister, None

    def get(self, request, minister_id):
        minister, err = self._get_minister_or_404(minister_id)
        if err:
            return err
        return Response(MinisterSerializer(minister).data)

    def patch(self, request, minister_id):
        minister, err = self._get_minister_or_404(minister_id)
        if err:
            return err
        serializer = MinisterSerializer(minister, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = minister_service.update_minister(minister, serializer.validated_data)
        except ValidationError as exc:
            return Response({"detail": exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MinisterSerializer(updated).data)

    def delete(self, request, minister_id):
        minister, err = self._get_minister_or_404(minister_id)
        if err:
            return err
        minister_service.delete_minister(minister)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MinisterFollowView(APIView):
    """
    POST   /users/ministers/<id>/follow/    — follow a minister
    DELETE /users/ministers/<id>/follow/    — unfollow a minister
    """

    permission_classes = [IsAuthenticated]

    def _get_minister_or_404(self, minister_id):
        minister = minister_service.get_minister_by_id(minister_id)
        if not minister:
            return None, Response({"detail": "Minister not found."}, status=status.HTTP_404_NOT_FOUND)
        return minister, None

    def post(self, request, minister_id):
        minister, err = self._get_minister_or_404(minister_id)
        if err:
            return err
        try:
            follow = minister_service.follow_minister(request.user, minister)
        except ValidationError as exc:
            return Response({"detail": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MinisterFollowSerializer(follow).data, status=status.HTTP_201_CREATED)

    def delete(self, request, minister_id):
        minister, err = self._get_minister_or_404(minister_id)
        if err:
            return err
        try:
            minister_service.unfollow_minister(request.user, minister)
        except ValidationError as exc:
            return Response({"detail": str(exc.message)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MinisterFollowersView(APIView):
    """
    GET /users/ministers/<id>/followers/   — list all followers of a minister
    """

    permission_classes = [AllowAny]

    def get(self, request, minister_id):
        minister = minister_service.get_minister_by_id(minister_id)
        if not minister:
            return Response({"detail": "Minister not found."}, status=status.HTTP_404_NOT_FOUND)
        followers = minister_service.get_minister_followers(minister)
        data = [
            {
                "user_id": f.user.id,
                "email": f.user.email,
                "username": f.user.username,
                "followed_at": f.followed_at,
            }
            for f in followers
        ]
        return Response(data)


class MyFollowingView(APIView):
    """
    GET /users/me/following/   — list ministers the current user follows
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        follows = minister_service.get_user_following(request.user)
        data = MinisterFollowSerializer(follows, many=True).data
        return Response(data)


class MinisterTagSearchView(APIView):
    """
    GET /users/ministers/tags/?q=<query>

    Returns a list of { id, name, tag } objects.
    - No query / empty query  → full list (served from cache, no DB hit after first request)
    - 1 char query            → full list returned (too short to filter; avoids per-keystroke DB load)
    - 2+ char query           → filtered from the in-memory cache (still no DB hit)

    The cache is automatically invalidated when any minister is created, updated, or deleted.
    """

    permission_classes = [AllowAny]

    MIN_QUERY_LENGTH = 2

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        effective_query = query if len(query) >= self.MIN_QUERY_LENGTH else None
        tags = minister_service.get_tags(effective_query)
        return Response(tags)
