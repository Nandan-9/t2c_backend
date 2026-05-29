from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError

from posts.services import post_service, vote_service


class VoteView(APIView):
    """
    POST   /posts/<post_id>/vote/   — cast or switch a vote
    DELETE /posts/<post_id>/vote/   — remove a vote

    Body: { "vote_type": "upvote" | "downvote" }

    POST behaviour:
      - No existing vote → creates; returns 201
      - Same vote_type again → 409
      - Different vote_type → switches; returns 200
    DELETE behaviour:
      - Matching vote exists → removed; returns 204
      - No matching vote → 400
    """

    permission_classes = [IsAuthenticated]

    def _get_post_or_404(self, post_id):
        post = post_service.get_post_by_id(post_id)
        if not post:
            return None, Response({"detail": "Post not found."}, status=status.HTTP_404_NOT_FOUND)
        return post, None

    def post(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err

        vote_type = request.data.get("vote_type")
        try:
            vote = vote_service.cast_vote(request.user, post, vote_type)
        except DRFValidationError as exc:
            code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
            if exc.detail and isinstance(exc.detail, dict) and exc.detail.get("code") == "already_voted":
                code = status.HTTP_409_CONFLICT
            return Response(exc.detail, status=code)

        from posts.models import Vote as VoteModel
        was_switch = hasattr(vote, "_state") and not vote._state.adding
        resp_status = status.HTTP_200_OK if was_switch else status.HTTP_201_CREATED
        return Response({"id": vote.id, "vote_type": vote.vote_type}, status=resp_status)

    def delete(self, request, post_id):
        post, err = self._get_post_or_404(post_id)
        if err:
            return err

        vote_type = request.data.get("vote_type")
        try:
            vote_service.remove_vote(request.user, post, vote_type)
        except DRFValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)
