from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Minister, MinisterFollow, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "is_staff", "is_active", "created_at")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("username", "avatar_url", "date_of_birth")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "is_staff", "is_active"),
        }),
    )


@admin.register(Minister)
class MinisterAdmin(admin.ModelAdmin):
    list_display = ("name", "dept", "constituency", "tag", "created_at")
    list_filter = ("dept",)
    search_fields = ("name", "dept", "constituency", "tag")
    readonly_fields = ("tag", "created_at")
    ordering = ("name",)

    fieldsets = (
        (None, {"fields": ("name", "dept", "constituency", "avatar_url")}),
        ("Auto-generated", {"fields": ("tag", "created_at")}),
    )


@admin.register(MinisterFollow)
class MinisterFollowAdmin(admin.ModelAdmin):
    list_display = ("user", "minister", "followed_at")
    list_filter = ("minister",)
    search_fields = ("user__email", "user__username", "minister__name", "minister__tag")
    readonly_fields = ("followed_at",)
    ordering = ("-followed_at",)
    raw_id_fields = ("user", "minister")
