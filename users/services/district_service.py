from django.db.models import Count, Q

from posts.models import Post
from users.models import District


def get_all_districts():
    return District.objects.order_by("name")


def get_districts_post_count():
    return (
        District.objects
        .annotate(post_count=Count("posts", filter=Q(posts__status=Post.STATUS_PUBLISHED)))
        .order_by("-post_count", "name")
    )


def get_district_by_id(district_id: int):
    try:
        return District.objects.get(pk=district_id)
    except District.DoesNotExist:
        return None


def create_district(data: dict) -> District:
    district = District(name=data["name"])
    district.full_clean()
    district.save()
    return district


def update_district(district: District, data: dict) -> District:
    if "name" in data:
        district.name = data["name"]
        district.full_clean()
        district.save(update_fields=["name"])
    return district


def delete_district(district: District) -> None:
    district.delete()
