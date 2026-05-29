import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings


def create_access_token(user):
    payload = {
        "user_id": user.id,
        "email": user.email,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=60),
        "iat": datetime.now(tz=timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user):
    payload = {
        "user_id": user.id,
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=30),
        "iat": datetime.now(tz=timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
