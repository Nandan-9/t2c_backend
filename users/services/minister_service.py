from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count

from users.models import Minister, MinisterFollow, User

_TAG_CACHE_KEY = "minister:all_tags"
_TAG_CACHE_TTL = 60  # seconds — invalidated on every minister save/delete


def _invalidate_tag_cache():
    cache.delete(_TAG_CACHE_KEY)


def get_tags(query: str | None) -> list[dict]:
    """
    Returns tags matching `query` (case-insensitive prefix match).
    Full list is cached for _TAG_CACHE_TTL seconds so rapid keystrokes
    hit memory, not the DB. Callers should enforce a minimum query length
    before calling this with a non-empty query.
    """
    all_tags = cache.get(_TAG_CACHE_KEY)
    if all_tags is None:
        all_tags = list(
            Minister.objects.order_by("tag").values("id", "name", "tag")
        )
        cache.set(_TAG_CACHE_KEY, all_tags, _TAG_CACHE_TTL)

    if not query:
        return all_tags

    q = query.lower()
    return [t for t in all_tags if q in t["tag"].lower() or q in t["name"].lower()]


def get_all_ministers():
    return (
        Minister.objects
        .annotate(total_posts=Count("tagged_posts"))
        .prefetch_related("departments")
        .order_by("name")
    )


def get_minister_by_id(minister_id: int) -> Minister:
    return (
        Minister.objects
        .annotate(total_posts=Count("tagged_posts"))
        .prefetch_related("departments")
        .filter(pk=minister_id)
        .first()
    )


def create_minister(data: dict) -> Minister:
    minister = Minister(
        name=data["name"],
        dept=data["dept"],
        constituency=data["constituency"],
        avatar_url=data.get("avatar_url", ""),
    )
    minister.full_clean()
    minister.save()
    _invalidate_tag_cache()
    return minister


def update_minister(minister: Minister, data: dict) -> Minister:
    for field in ("name", "dept", "constituency", "avatar_url"):
        if field in data:
            setattr(minister, field, data[field])
    minister.full_clean()
    minister.save()
    _invalidate_tag_cache()
    return minister


def delete_minister(minister: Minister) -> None:
    minister.delete()
    _invalidate_tag_cache()


def follow_minister(user: User, minister: Minister) -> MinisterFollow:
    follow, created = MinisterFollow.objects.get_or_create(user=user, minister=minister)
    if not created:
        raise ValidationError("You are already following this minister.")
    return follow


def unfollow_minister(user: User, minister: Minister) -> None:
    deleted, _ = MinisterFollow.objects.filter(user=user, minister=minister).delete()
    if not deleted:
        raise ValidationError("You are not following this minister.")


def get_minister_followers(minister: Minister):
    return minister.followers.select_related("user").order_by("-followed_at")


def get_user_following(user: User):
    return user.following_ministers.select_related("minister").order_by("-followed_at")
