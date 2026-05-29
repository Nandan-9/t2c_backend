from django.contrib import admin

from .models import RefreshToken


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "is_revoked", "expires_at", "created_at")
    list_filter = ("is_revoked",)
    search_fields = ("user__email", "user__username")
    readonly_fields = ("token", "expires_at", "created_at")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)

    def has_add_permission(self, request):
        return False
