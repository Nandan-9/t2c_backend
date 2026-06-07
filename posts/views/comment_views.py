from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import Comment
from posts.serializers import CommentSerializer
from posts.services import comment_service, post_service


class CommentListCreateView(APIView):
    """
    GET  /posts/<post_id>/comments/  — list comments, oldest first
    POST /posts/<post_id>/comments/  — add a comment
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def _get_post_or_404(self, post_id):
        post = post_service.get_post_by_id(post_id)
        if not post:
            return None, Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        return post, None

    def get(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err
        comments = comment_service.get_comments_for_post(post)
        data = CommentSerializer(comments, many=True).data
        return Response(data)

    def post(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err
        serializer = CommentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        parent = None
        parent_id = request.data.get("parent_id")
        if parent_id:
            try:
                parent = Comment.objects.get(pk=parent_id, post=post)
            except Comment.DoesNotExist:
                return Response(
                    {"detail": "Parent comment not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        comment = comment_service.create_comment(
            author=request.user,
            post=post,
            content=serializer.validated_data["content"],
            parent=parent,
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    """
    DELETE /posts/<post_id>/comments/<comment_id>/  — delete (author or admin)
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, post_id, comment_id):
        try:
            comment = Comment.objects.select_related("author").get(pk=comment_id, post_id=post_id)
        except Exception:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)

        if comment.author != request.user and not request.user.is_staff:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        comment_service.delete_comment(comment)
        return Response(status=status.HTTP_204_NO_CONTENT)
