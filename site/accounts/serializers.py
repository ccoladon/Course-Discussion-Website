from rest_framework import serializers

from .models import UserProfile


class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="public_name", read_only=True)
    university = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = UserProfile
        fields = ["user_id", "email", "name", "display_name", "role", "is_verified", "university"]
        read_only_fields = ["user_id", "email", "name", "role", "is_verified", "university"]


class RequestCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class ConfirmCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the 6-digit code."})

    def validate_email(self, value: str) -> str:
        return value.strip().lower()
