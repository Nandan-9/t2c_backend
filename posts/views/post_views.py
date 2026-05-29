from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.serializers import PostDetailSerializer, PostSerializer
from posts.services import post_service
from users.models import Minister


class FeedView(APIView):
    """
    GET /posts/feed/?page=1
    Returns a randomised interleave of:
      - Pool A: all posts ranked by upvote count
      - Pool B: posts tagged to ministers the user follows, ranked by upvote count
    Response is cached in Redis for 120 s per user+page.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        page = max(1, int(request.query_params.get("page", 1)))
        feed = post_service.get_feed_from_cache_or_db(request.user, page=page)
        serializer = PostSerializer(feed["results"], many=True, context={"request": request})
        print(serializer.data)
        return Response({
            "count": feed["count"],
            "page": feed["page"],
            "page_size": feed["page_size"],
            "results": serializer.data,
        })


class PostListCreateView(APIView):
    """
    GET  /posts/  — all posts, newest first (admin only)
    POST /posts/  — create a post (any authenticated user)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get(self, request):
        posts = post_service.get_all_posts()
        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response(data)

    def post(self, request):
        serializer = PostSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        minister = None
        minister_id = serializer.validated_data.pop("minister_id", None)
        if minister_id:
            try:
                minister = Minister.objects.get(pk=minister_id)
            except Minister.DoesNotExist:
                return Response({"detail": "Minister not found."}, status=status.HTTP_404_NOT_FOUND)

        post = post_service.create_post(
            request.user,
            {
                "heading": serializer.validated_data["heading"],
                "content": serializer.validated_data["content"],
                "minister": minister,
                "media_key": serializer.validated_data.get("media_key"),
                "media_type": serializer.validated_data.get("media_type"),
            },
        )
        return Response(PostSerializer(post, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    """
    GET    /posts/<post_id>/  — post detail with comments + vote counts
    PATCH  /posts/<post_id>/  — edit content (author only)
    DELETE /posts/<post_id>/  — delete (author or admin)
    """

    permission_classes = [IsAuthenticated]

    def _get_or_404(self, post_id, viewer=None):
        post = post_service.get_post_by_id(post_id, viewer=viewer)
        if not post:
            return None, Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        return post, None

    def get(self, request, post_id):
        post, err = self._get_or_404(post_id, viewer=request.user)
        if err:
            return err
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    def patch(self, request, post_id):
        post, err = self._get_or_404(post_id, viewer=request.user)
        if err:
            return err
        if post.author != request.user:
            return Response({"detail": "You can only edit your own posts."}, status=status.HTTP_403_FORBIDDEN)
        serializer = PostSerializer(post, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = post_service.update_post(post, serializer.validated_data)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PostSerializer(updated, context={"request": request}).data)

    def delete(self, request, post_id):
        post, err = self._get_or_404(post_id, viewer=request.user)
        if err:
            return err
        if post.author != request.user and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        post_service.delete_post(post)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MinisterPostsView(APIView):
    """
    GET /posts/minister/<minister_id>/  — posts tagged to a specific minister
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, minister_id):
        try:
            minister = Minister.objects.get(pk=minister_id)
        except Minister.DoesNotExist:
            return Response({"detail": "Minister not found."}, status=status.HTTP_404_NOT_FOUND)

        posts = post_service.get_posts_by_minister(minister)
        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response(data)
