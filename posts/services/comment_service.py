from django.core.exceptions import ValidationError
from django.db.models import Prefetch

from posts.models import Comment, Post


def create_comment(author, post: Post, content: str, parent=None) -> Comment:
    comment = Comment(author=author, post=post, content=content, parent=parent)
    comment.full_clean()
    comment.save()
    return comment


def get_comments_for_post(post: Post):
    l3 = Comment.objects.select_related("author")
    l2 = Comment.objects.select_related("author").prefetch_related(
        Prefetch("replies", queryset=l3)
    )
    l1 = Comment.objects.select_related("author").prefetch_related(
        Prefetch("replies", queryset=l2)
    )
    return (
        Comment.objects.filter(post=post, parent=None)
        .select_related("author")
        .prefetch_related(Prefetch("replies", queryset=l1))
        .order_by("created_at")
    )


def delete_comment(comment: Comment) -> None:
    comment.delete()
