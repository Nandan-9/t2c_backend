import re

from rest_framework import serializers

from .models import Minister, MinisterFollow, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "avatar_url", "date_of_birth"]
        read_only_fields = ["id", "email", "avatar_url"]

    def validate_username(self, value):
        if len(value) < 3 or len(value) > 30:
            raise serializers.ValidationError("Username must be between 3 and 30 characters.")
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise serializers.ValidationError("Username may only contain letters, digits, and underscores.")
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This username is already taken.")
        return value


class MinisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Minister
        fields = ["id", "name", "dept", "constituency", "avatar_url", "tag", "created_at"]
        read_only_fields = ["id", "tag", "created_at"]


class MinisterFollowSerializer(serializers.ModelSerializer):
    minister = MinisterSerializer(read_only=True)

    class Meta:
        model = MinisterFollow
        fields = ["id", "minister", "followed_at"]
        read_only_fields = ["id", "followed_at"]
