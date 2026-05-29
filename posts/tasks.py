import logging

import redis as redis_lib
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import F

logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.REDIS_VOTES_URL, decode_responses=True)


@shared_task(
    bind=True,
    acks_late=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    queue="votes",
)
def flush_vote_counts(self, post_id: int) -> None:
    """
    Reads the accumulated vote delta from Redis and applies it to Post.cached_upvote_count.
    Uses GETDEL so the delta is atomically consumed; on failure the raw value is logged
    before the retry so the delta is never silently lost.
    """
    from posts.models import Post

    delta = None
    try:
        raw = _redis.getdel(f"vote_delta:{post_id}")
        delta = int(raw) if raw is not None else 0
        if delta == 0:
            return

        Post.objects.filter(pk=post_id).update(
            cached_upvote_count=F("cached_upvote_count") + delta
        )

        # Invalidate all feed caches so the updated count surfaces
        cache.delete_pattern("feed:*")

    except Exception as exc:
        logger.error(
            "flush_vote_counts FAILED post_id=%s delta=%s error=%s — will retry",
            post_id,
            delta,
            exc,
        )
        # Restore the delta to Redis so it isn't lost on retry
        if delta:
            _redis.incrby(f"vote_delta:{post_id}", delta)
        raise
