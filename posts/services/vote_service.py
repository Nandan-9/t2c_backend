import logging

import redis as redis_lib
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from posts.models import Post, Vote

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_VOTES_URL, decode_responses=True)

UPVOTE = Vote.UPVOTE
DOWNVOTE = Vote.DOWNVOTE


def _delta_key(post_id: int) -> str:
    return f"vote_delta:{post_id}"


def _apply_redis_delta(post_id: int, delta: int) -> None:
    if delta != 0:
        _redis.incrby(_delta_key(post_id), delta)


def cast_vote(user, post: Post, vote_type: str) -> Vote:
    """
    - Same vote_type again → raise 409
    - Switching vote type → update record, delta ±2
    - New vote → create, delta ±1
    """
    if vote_type not in (UPVOTE, DOWNVOTE):
        raise DRFValidationError({"detail": "vote_type must be 'upvote' or 'downvote'."})

    try:
        existing = Vote.objects.get(post=post, user=user)
    except Vote.DoesNotExist:
        existing = None

    if existing is not None:
        if existing.vote_type == vote_type:
            raise DRFValidationError(
                {"detail": f"You have already {vote_type}d this post.", "code": "already_voted"},
                code=409,
            )
        # Switching: up→down = -2, down→up = +2
        delta = -2 if vote_type == DOWNVOTE else 2
        existing.vote_type = vote_type
        existing.save(update_fields=["vote_type"])
        _apply_redis_delta(post.id, delta)
        _trigger_flush(post.id)
        return existing

    # New vote
    vote = Vote.objects.create(post=post, user=user, vote_type=vote_type)
    delta = 1 if vote_type == UPVOTE else -1
    _apply_redis_delta(post.id, delta)
    _trigger_flush(post.id)
    return vote


def remove_vote(user, post: Post, vote_type: str) -> None:
    """
    Removes a vote. Raises 404 if no matching vote found.
    Delta: -1 for removing an upvote, +1 for removing a downvote.
    """
    if vote_type not in (UPVOTE, DOWNVOTE):
        raise DRFValidationError({"detail": "vote_type must be 'upvote' or 'downvote'."})

    deleted, _ = Vote.objects.filter(post=post, user=user, vote_type=vote_type).delete()
    if not deleted:
        raise DRFValidationError({"detail": f"You have not {vote_type}d this post."})

    delta = -1 if vote_type == UPVOTE else 1
    _apply_redis_delta(post.id, delta)
    _trigger_flush(post.id)


def _trigger_flush(post_id: int) -> None:
    from posts.tasks import flush_vote_counts
    flush_vote_counts.apply_async((post_id,), countdown=5)
