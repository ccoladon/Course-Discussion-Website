from rest_framework import serializers

from .models import Channel, Message, Report


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "channel",
            "body",
            "author",
            "parent",
            "is_answer",
            "is_pinned",
            "reply_count",
            "created_at",
            "edited_at",
            "deleted_at",
        ]

    def get_author(self, obj):
        profile = getattr(obj.author, "profile", None)
        return {
            "id": obj.author_id,
            "name": profile.public_name if profile else obj.author.username,
        }

    def get_reply_count(self, obj):
        return getattr(obj, "reply_count", 0)


class ChannelSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="section.course.code", read_only=True)
    section_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Channel
        fields = ["id", "name", "kind", "section_id", "course_code"]


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=10_000)
    parent = serializers.IntegerField(required=False, allow_null=True)


class ReportCreateSerializer(serializers.Serializer):
    message = serializers.IntegerField()
    reason = serializers.CharField(max_length=500)
