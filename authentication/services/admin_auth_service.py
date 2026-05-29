import jwt
from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError

from authentication.models import RefreshToken
from core.tokens import create_access_token, create_refresh_token

User = get_user_model()


def login_admin(email: str, password: str) -> dict:
    """
    Validates credentials and verifies the user is staff.
    Returns tokens + user info dict on success, raises on failure.
    """
    if not email or not password:
        raise ValidationError({"detail": "email and password are required."})

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise AuthenticationFailed("Invalid credentials.")

    if not user.check_password(password):
        raise AuthenticationFailed("Invalid credentials.")

    if not user.is_active:
        raise AuthenticationFailed("This account is inactive.")

    if not user.is_staff:
        raise PermissionDenied("You do not have admin access.")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    _store_refresh_token(user, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "is_staff": user.is_staff,
        },
    }


def logout_admin(user: User, raw_refresh_token: str) -> None:
    """
    Revokes the given refresh token for the user.
    Raises ValidationError if token is not found.
    """
    revokable = RefreshToken.objects.filter(token=raw_refresh_token, user=user)
    if not revokable.exists():
        raise ValidationError({"detail": "Token not found."})
    revokable.update(is_revoked=True)


def _store_refresh_token(user: User, token: str) -> None:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    RefreshToken.objects.create(user=user, token=token, expires_at=expires_at)
