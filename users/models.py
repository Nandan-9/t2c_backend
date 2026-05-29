from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.text import slugify


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    avatar_url = models.URLField(blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


def _generate_tag(name: str, dept: str) -> str:
    return f"@{slugify(name)}_{slugify(dept)}"


class Minister(models.Model):
    name = models.CharField(max_length=200)
    dept = models.CharField(max_length=200)
    constituency = models.CharField(max_length=200)
    avatar_url = models.URLField(blank=True, default="")
    tag = models.CharField(max_length=255, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.tag = _generate_tag(self.name, self.dept)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.tag})"


class MinisterFollow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_ministers")
    minister = models.ForeignKey(Minister, on_delete=models.CASCADE, related_name="followers")
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "minister")

    def __str__(self):
        return f"{self.user.email} → {self.minister.tag}"
