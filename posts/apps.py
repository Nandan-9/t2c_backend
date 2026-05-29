import logging
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class PostsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "posts"

    def ready(self):
        import sys
        # Skip the Redis health check when running management commands (migrate,
        # makemigrations, shell, test, etc.) so those work without Redis running.
        _SKIP_COMMANDS = {
            "makemigrations", "migrate", "collectstatic", "shell",
            "test", "createsuperuser", "dbshell", "showmigrations", "check",
        }
        if len(sys.argv) > 1 and sys.argv[1] in _SKIP_COMMANDS:
            return

        from django.conf import settings
        import redis as redis_lib

        votes_url = getattr(settings, "REDIS_VOTES_URL", None)
        if not votes_url:
            raise ImproperlyConfigured("REDIS_VOTES_URL must be set in settings.")

        try:
            client = redis_lib.from_url(votes_url, socket_connect_timeout=2)
            client.ping()
            policy_result = client.config_get("maxmemory-policy")
            policy = policy_result.get("maxmemory-policy", "")
            if policy != "noeviction":
                raise ImproperlyConfigured(
                    f"REDIS_VOTES_URL maxmemory-policy must be 'noeviction', got '{policy}'. "
                    "Set it in redis.conf or via: redis-cli CONFIG SET maxmemory-policy noeviction"
                )
        except redis_lib.exceptions.ConnectionError as exc:
            raise ImproperlyConfigured(
                f"Cannot connect to REDIS_VOTES_URL ({votes_url}): {exc}"
            ) from exc
