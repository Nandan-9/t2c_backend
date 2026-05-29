from django.urls import path
from .views import AdminLoginView, AdminLogoutView, GoogleOAuthView, LogoutView, TokenRefreshView

urlpatterns = [
    path("google/", GoogleOAuthView.as_view(), name="google-oauth"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
]
