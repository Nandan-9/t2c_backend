import json
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from posts.models import Post, Vote

POST_EDIT_WINDOW_SECONDS = 900  # 15 minutes

User = get_user_model()

FEED_CACHE_TTL = 120  # seconds
FEED_POOL_SIZE = 50   # posts fetched per pool before merge


def _feed_cache_key(user_id: int, page: int) -> str:
    return f"feed:{user_id}:{page}"


def _annotated_qs():
    return Post.objects.annotate(
        upvote_count=Count("votes", filter=Q(votes__vote_type=Vote.UPVOTE)),
        downvote_count=Count("votes", filter=Q(votes__vote_type=Vote.DOWNVOTE)),
    ).select_related("author", "minister", "department")


def create_post(author, data: dict) -> Post:
    department = data.get("department")
    minister = data.get("minister") or (department.minister if department else None)

    post = Post(
        author=author,
        heading=data["heading"],
        content=data["content"],
        department=department,
        minister=minister,
        media_key=data.get("media_key"),
        media_type=data.get("media_type") or "",
    )
    post.full_clean()
    post.save()
    _invalidate_feed_cache(author.id)
    return post


def get_post_by_id(post_id: int, viewer=None):
    try:
        post = _annotated_qs().prefetch_related("comments__author").get(pk=post_id)
    except Post.DoesNotExist:
        return None

    if post.status == Post.STATUS_DELETED:
        return None

    if viewer and viewer.id == post.author_id:
        # Owner sees all non-deleted statuses
        return post

    if post.status != Post.STATUS_PUBLISHED:
        return None

    return post


def get_all_posts():
    return _annotated_qs().exclude(status=Post.STATUS_DELETED).order_by("-created_at")


def get_posts_by_minister(minister):
    return (
        _annotated_qs()
        .filter(minister=minister, status=Post.STATUS_PUBLISHED)
        .order_by("-created_at")
    )


def is_within_edit_window(post: Post) -> bool:
    return (timezone.now() - post.created_at).total_seconds() <= POST_EDIT_WINDOW_SECONDS


def get_feed(user, page: int = 1, page_size: int = 20) -> dict:
    cache_key = _feed_cache_key(user.id, page)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    followed_ministers = list(
        user.following_ministers.values_list("minister_id", flat=True)
    )

    published_qs = _annotated_qs().filter(status=Post.STATUS_PUBLISHED)

    # Pool A: all published posts sorted by cached_upvote_count
    pool_a = list(
        published_qs
        .order_by("-cached_upvote_count")[:FEED_POOL_SIZE]
    )

    # Pool B: published posts tagged to followed ministers sorted by cached_upvote_count
    # pool_b = list(
    #     published_qs
    #     .filter(minister_id__in=followed_ministers)
    #     .order_by("-cached_upvote_count", "-created_at")[:FEED_POOL_SIZE]
    # ) if followed_ministers else []
    pool_b = []

    # Merge + deduplicate, preserving objects
    seen_ids = set()
    merged = []
    for post in pool_a + pool_b:
        if post.id not in seen_ids:
            seen_ids.add(post.id)
            merged.append(post)

    # Seeded shuffle so same user gets consistent ordering per page number
    # rng = random.Random(user.id + page * 9973)
    # rng.shuffle(merged)

    # Paginate
    start = (page - 1) * page_size
    page_posts = merged[start: start + page_size]

    result = {
        "count": len(merged),
        "page": page,
        "page_size": page_size,
        "results": page_posts,
    }

    # Cache the queryset objects can't be JSON-serialised directly; cache the
    # post id list and re-fetch on miss instead. Return the ORM objects here;
    # the view/serializer will handle serialization.
    id_list = [p.id for p in page_posts]
    cache.set(cache_key, {"count": result["count"], "page": page, "page_size": page_size, "post_ids": id_list}, FEED_CACHE_TTL)

    return result


def get_feed_from_cache_or_db(user, page: int = 1, page_size: int = 20) -> dict:
    """
    Returns dict with ORM Post objects in 'results'.
    Checks Redis for cached post_ids first; re-fetches full objects if hit.
    """
    cache_key = _feed_cache_key(user.id, page)
    cached = cache.get(cache_key)

    if cached is not None and "post_ids" in cached:
        posts = list(_annotated_qs().filter(id__in=cached["post_ids"], status=Post.STATUS_PUBLISHED))
        id_order = {pid: idx for idx, pid in enumerate(cached["post_ids"])}
        posts.sort(key=lambda p: id_order.get(p.id, 0))
        return {
            "count": cached["count"],
            "page": cached["page"],
            "page_size": cached["page_size"],
            "results": posts,
        }

    return get_feed(user, page, page_size)


def update_post(post: Post, data: dict) -> Post:
    if not is_within_edit_window(post):
        raise PermissionError("Post can only be edited within 15 minutes of creation.")

    allowed_status_values = {Post.STATUS_PUBLISHED, Post.STATUS_ARCHIVED, Post.STATUS_DRAFT}
    new_status = data.get("status")
    if new_status is not None and new_status not in allowed_status_values:
        raise ValueError(f"status must be one of {sorted(allowed_status_values)}.")

    update_fields = ["updated_at"]
    if "heading" in data:
        post.heading = data["heading"]
        update_fields.append("heading")
    if "content" in data:
        post.content = data["content"]
        update_fields.append("content")
    if new_status is not None:
        post.status = new_status
        update_fields.append("status")

    post.full_clean()
    post.save(update_fields=update_fields)
    _invalidate_feed_cache(post.author_id)
    return post


def delete_post(post: Post) -> None:
    post.status = Post.STATUS_DELETED
    post.save(update_fields=["status", "updated_at"])
    _invalidate_feed_cache(post.author_id)


def _invalidate_feed_cache(user_id: int) -> None:
    cache.delete_pattern(f"feed:{user_id}:*")
