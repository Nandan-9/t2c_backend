from django.core.exceptions import ValidationError

from posts.models import Comment, Post


def create_comment(author, post: Post, content: str) -> Comment:
    comment = Comment(author=author, post=post, content=content)
    comment.full_clean()
    comment.save()
    return comment


def get_comments_for_post(post: Post):
    return post.comments.select_related("author").order_by("created_at")


def delete_comment(comment: Comment) -> None:
    comment.delete()
