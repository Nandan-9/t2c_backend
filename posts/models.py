from django.conf import settings
from django.db import models
from users.models import District

class Post(models.Model):
    MEDIA_TYPE_IMAGE = "image"
    MEDIA_TYPE_VIDEO = "video"
    MEDIA_TYPE_CHOICES = [
        (MEDIA_TYPE_IMAGE, "Image"),
        (MEDIA_TYPE_VIDEO, "Video"),
    ]

    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_DRAFT = "draft"
    STATUS_DELETED = "deleted"
    STATUS_CHOICES = [
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
        (STATUS_DRAFT, "Draft"),
        (STATUS_DELETED, "Deleted"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    minister = models.ForeignKey(
        "users.Minister",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tagged_posts",
    )
    department = models.ForeignKey(
        "users.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    heading = models.CharField(max_length=300)
    content = models.TextField()
    media_key = models.CharField(max_length=500, blank=True, null=True)
    media_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, blank=True, null=True
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PUBLISHED, db_index=True
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    cached_upvote_count = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"Post({self.id}) by {self.author.email}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    parent      = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment({self.id}) on Post({self.post_id}) by {self.author.email}"


class Vote(models.Model):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    VOTE_CHOICES = [(UPVOTE, "Upvote"), (DOWNVOTE, "Downvote")]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes"
    )
    vote_type = models.CharField(max_length=8, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.vote_type} on Post({self.post_id}) by {self.user.email}"
