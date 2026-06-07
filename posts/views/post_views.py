from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.serializers import PostDetailSerializer, PostSerializer
from posts.services import post_service
from users.models import Department, District, Minister


class FeedView(APIView):
    """
    GET /posts/feed/                                              — first page
    GET /posts/feed/?cursor_upvote_count=...&cursor_id=...       — next page
    """

    permission_classes = [AllowAny]

    def get(self, request):
        raw_upvote = request.query_params.get("cursor_upvote_count")
        raw_id = request.query_params.get("cursor_id")

        cursor_upvote_count = int(raw_upvote) if raw_upvote is not None else None
        cursor_id = int(raw_id) if raw_id is not None else None

        posts = post_service.get_feed_cursor(
            request.user,
            cursor_upvote_count=cursor_upvote_count,
            cursor_id=cursor_id,
        )

        next_cursor_upvote_count = None
        next_cursor_id = None
        if posts:
            last = posts[-1]
            next_cursor_upvote_count = last.cached_upvote_count
            next_cursor_id = last.id

        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response({
            "results": data,
            "next_cursor_upvote_count": next_cursor_upvote_count,
            "next_cursor_id": next_cursor_id,
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

        minister_ids = serializer.validated_data.pop("minister_ids", [])
        ministers = list(Minister.objects.filter(pk__in=minister_ids))
        if len(ministers) != len(set(minister_ids)):
            return Response({"detail": "One or more ministers not found."}, status=status.HTTP_404_NOT_FOUND)

        department_ids = serializer.validated_data.pop("department_ids", [])
        departments = list(Department.objects.filter(pk__in=department_ids))
        if len(departments) != len(set(department_ids)):
            return Response({"detail": "One or more departments not found."}, status=status.HTTP_404_NOT_FOUND)

        district = None
        district_id = serializer.validated_data.pop("district_id", None)
        if district_id:
            try:
                district = District.objects.get(pk=district_id)
            except District.DoesNotExist:
                return Response({"detail": "District not found."}, status=status.HTTP_404_NOT_FOUND)

        post = post_service.create_post(
            request.user,
            {
                "heading": serializer.validated_data["heading"],
                "content": serializer.validated_data["content"],
                "ministers": ministers,
                "departments": departments,
                "district": district,
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

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

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

        update_data = dict(serializer.validated_data)

        if "minister_ids" in request.data:
            minister_ids = update_data.pop("minister_ids", [])
            ministers = list(Minister.objects.filter(pk__in=minister_ids))
            if len(ministers) != len(set(minister_ids)):
                return Response({"detail": "One or more ministers not found."}, status=status.HTTP_404_NOT_FOUND)
            update_data["ministers"] = ministers
        else:
            update_data.pop("minister_ids", None)

        if "department_ids" in request.data:
            department_ids = update_data.pop("department_ids", [])
            departments = list(Department.objects.filter(pk__in=department_ids))
            if len(departments) != len(set(department_ids)):
                return Response({"detail": "One or more departments not found."}, status=status.HTTP_404_NOT_FOUND)
            update_data["departments"] = departments
        else:
            update_data.pop("department_ids", None)

        try:
            updated = post_service.update_post(post, update_data)
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


class TrendingPostsView(APIView):
    """
    GET /posts/trending/                                          — first page (top 20 by upvotes)
    GET /posts/trending/?cursor_upvote_count=...&cursor_id=...   — next page
    """

    permission_classes = [AllowAny]

    def get(self, request):
        raw_upvote = request.query_params.get("cursor_upvote_count")
        raw_id = request.query_params.get("cursor_id")

        cursor_upvote_count = int(raw_upvote) if raw_upvote is not None else None
        cursor_id = int(raw_id) if raw_id is not None else None

        posts = list(post_service.get_trending_posts(
            cursor_upvote_count=cursor_upvote_count,
            cursor_id=cursor_id,
        ))

        next_cursor_upvote_count = None
        next_cursor_id = None
        if posts:
            last = posts[-1]
            next_cursor_upvote_count = last.cached_upvote_count
            next_cursor_id = last.id

        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response({
            "results": data,
            "next_cursor_upvote_count": next_cursor_upvote_count,
            "next_cursor_id": next_cursor_id,
        })


class LatestPostsView(APIView):
    """
    GET /posts/latest/                                        — first page (newest 20)
    GET /posts/latest/?cursor_created_at=...&cursor_id=...   — next page
    """

    permission_classes = [AllowAny]

    def get(self, request):
        cursor_created_at = request.query_params.get("cursor_created_at")
        cursor_id = request.query_params.get("cursor_id")

        posts = list(post_service.get_latest_posts(
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        ))

        next_cursor_created_at = None
        next_cursor_id = None
        if posts:
            last = posts[-1]
            next_cursor_created_at = last.created_at.isoformat()
            next_cursor_id = last.id

        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response({
            "results": data,
            "next_cursor_created_at": next_cursor_created_at,
            "next_cursor_id": next_cursor_id,
        })

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


class MinistersBulkPostsView(APIView):
    """
    GET /posts/ministers/?ids=1,2,3
    GET /posts/ministers/?ids=1,2,3&cursor_upvote_count=5&cursor_created_at=...&cursor_id=42
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("ids", "")
        try:
            minister_ids = [int(i) for i in raw.split(",") if i.strip()]
        except ValueError:
            return Response({"detail": "ids must be a comma-separated list of integers."}, status=status.HTTP_400_BAD_REQUEST)

        if not minister_ids:
            return Response({"detail": "Provide at least one minister id via ?ids=1,2,3"}, status=status.HTTP_400_BAD_REQUEST)

        raw_upvote = request.query_params.get("cursor_upvote_count")
        raw_created_at = request.query_params.get("cursor_created_at")
        raw_id = request.query_params.get("cursor_id")

        cursor_upvote_count = int(raw_upvote) if raw_upvote is not None else None
        cursor_created_at = raw_created_at if raw_created_at is not None else None
        cursor_id = int(raw_id) if raw_id is not None else None

        posts = list(post_service.get_posts_by_ministers(
            minister_ids,
            cursor_upvote_count=cursor_upvote_count,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        ))

        next_cursor_upvote_count = None
        next_cursor_created_at = None
        next_cursor_id = None
        if posts:
            last = posts[-1]
            next_cursor_upvote_count = last.cached_upvote_count
            next_cursor_created_at = last.created_at.isoformat()
            next_cursor_id = last.id

        data = PostSerializer(posts, many=True, context={"request": request}).data
        return Response({
            "results": data,
            "next_cursor_upvote_count": next_cursor_upvote_count,
            "next_cursor_created_at": next_cursor_created_at,
            "next_cursor_id": next_cursor_id,
        })
