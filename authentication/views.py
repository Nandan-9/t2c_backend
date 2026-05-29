import jwt
import requests
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from core.tokens import create_access_token, create_refresh_token
from .models import RefreshToken
from .services import admin_auth_service

User = get_user_model()

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _store_refresh_token(user, token: str) -> None:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    RefreshToken.objects.create(user=user, token=token, expires_at=expires_at)


class GoogleOAuthView(APIView):
    """
    POST /auth/google/
    Body: { "code": "<Google auth code>", "redirect_uri": "<frontend redirect URI>" }

    Exchanges the Google auth code for user info, creates or fetches the user,
    then returns the app's own JWT access + refresh tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        print("comming")
        code = request.data.get("code")
        redirect_uri = request.data.get("redirect_uri")

        if not code or not redirect_uri:
            return Response(
                {"detail": "code and redirect_uri are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange code for Google tokens
        token_response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )

        if not token_response.ok:
            return Response(
                {"detail": "Failed to exchange code with Google.", "google_error": token_response.json()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        google_access_token = token_response.json().get("access_token")

        # Fetch user profile from Google
        userinfo_response = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )

        if not userinfo_response.ok:
            return Response(
                {"detail": "Failed to fetch user info from Google."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = userinfo_response.json()
        email = profile.get("email")
        name = profile.get("name", "")
        picture = profile.get("picture", "")

        if not email:
            return Response(
                {"detail": "Google account has no email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Derive a unique username from the email local-part
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exclude(email=email).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": username, "avatar_url": picture},
        )

        # Update avatar if it changed
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            user.save(update_fields=["avatar_url"])

        access_token = create_access_token(user)
        refresh_token = create_refresh_token(user)
        _store_refresh_token(user, refresh_token)

        return Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "is_new_user": created,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                },
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """
    POST /auth/token/refresh/
    Body: { "refresh_token": "<token>" }

    Returns a new access token if the refresh token is valid and not revoked.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.data.get("refresh_token")
        if not raw_token:
            return Response({"detail": "refresh_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = jwt.decode(raw_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return Response({"detail": "Refresh token has expired."}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("type") != "refresh":
            return Response({"detail": "Invalid token type."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            stored = RefreshToken.objects.get(token=raw_token)
        except RefreshToken.DoesNotExist:
            return Response({"detail": "Refresh token not recognised."}, status=status.HTTP_401_UNAUTHORIZED)

        if stored.is_revoked:
            return Response({"detail": "Refresh token has been revoked."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_401_UNAUTHORIZED)

        new_access_token = create_access_token(user)

        return Response(
            {"access_token": new_access_token, "token_type": "Bearer"},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /auth/logout/
    Header: Authorization: Bearer <access_token>

    Revokes the supplied refresh token so it can no longer be used.
    Body: { "refresh_token": "<token>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_token = request.data.get("refresh_token")
        if not raw_token:
            return Response({"detail": "refresh_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        RevokableToken = RefreshToken.objects.filter(token=raw_token, user=request.user)
        if not RevokableToken.exists():
            return Response({"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND)

        RevokableToken.update(is_revoked=True)
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class AdminLoginView(APIView):
    """
    POST /auth/admin/login/
    Body: { "email": "...", "password": "..." }

    Returns JWT tokens only for users with is_staff=True.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")
        try:
            result = admin_auth_service.login_admin(email, password)
        except Exception as exc:
            code = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
            detail = getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=code)
        return Response(result, status=status.HTTP_200_OK)


class AdminLogoutView(APIView):
    """
    POST /auth/admin/logout/
    Header: Authorization: Bearer <access_token>
    Body: { "refresh_token": "..." }

    Revokes the refresh token. Admin-only route.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        raw_token = request.data.get("refresh_token")
        if not raw_token:
            return Response({"detail": "refresh_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            admin_auth_service.logout_admin(request.user, raw_token)
        except Exception as exc:
            detail = getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)
