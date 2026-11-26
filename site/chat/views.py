from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Enrollment
from courses.permissions import can_moderate_section, is_enrolled_in_course

from .models import Channel, Message, Report
from .serializers import (
    MessageCreateSerializer,
    MessageSerializer,
    ReportCreateSerializer,
)

PAGE_SIZE = 50


def _channel_for_user(request, channel_id: int) -> Channel:
    channel = get_object_or_404(
        Channel.objects.select_related("section__course"), pk=channel_id
    )
    if not is_enrolled_in_course(request.user, channel.section.course_id):
        raise PermissionDenied("Join this course first.")
    return channel


def _broadcast(channel_id: int, message: Message):
    """Push a REST-created message to WebSocket subscribers too."""
    layer = get_channel_layer()
    if layer is None:
        return
    payload = MessageSerializer(message).data
    async_to_sync(layer.group_send)(
        f"channel_{channel_id}", {"type": "chat.message", "message": payload}
    )


class ChannelMessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        channel = _channel_for_user(request, pk)
        queryset = (
            channel.messages.filter(parent__isnull=True, deleted_at__isnull=True)
            .select_related("author__profile")
            .annotate(
                reply_count=Count(
                    "replies", filter=Q(replies__deleted_at__isnull=True), distinct=True
                )
            )
        )

        before = request.query_params.get("before")
        if before:
            queryset = queryset.filter(id__lt=before)

        items = list(queryset.order_by("-id")[: PAGE_SIZE + 1])
        has_more = len(items) > PAGE_SIZE
        items = items[:PAGE_SIZE][::-1]

        return Response(
            {
                "results": MessageSerializer(items, many=True).data,
                "has_more": has_more,
                "next_before": items[0].id if has_more and items else None,
            }
        )

    def post(self, request, pk):
        channel = _channel_for_user(request, pk)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        parent = None
        parent_id = serializer.validated_data.get("parent")
        if parent_id:
            parent = channel.messages.filter(pk=parent_id, parent__isnull=True).first()
            if parent is None:
                raise ValidationError({"parent": "Reply to a top-level message in this channel."})

        message = Message.objects.create(
            channel=channel,
            author=request.user,
            body=serializer.validated_data["body"],
            parent=parent,
        )
        _broadcast(channel.id, message)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class MessageRepliesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        message = get_object_or_404(
            Message.objects.select_related("channel__section"), pk=pk
        )
        _channel_for_user(request, message.channel_id)
        replies = message.replies.filter(deleted_at__isnull=True).select_related(
            "author__profile"
        )
        return Response(MessageSerializer(replies, many=True).data)


class MessageAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        message = get_object_or_404(
            Message.objects.select_related("channel__section"), pk=pk
        )
        channel = _channel_for_user(request, message.channel_id)
        if message.parent_id is not None:
            raise ValidationError({"detail": "Only top-level questions can be marked answered."})

        can_mark = (
            message.author_id == request.user.id
            or can_moderate_section(request.user, channel.section)
        )
        if not can_mark:
            raise PermissionDenied("Only the asker or a course moderator can mark an answer.")

        message.is_answer = not message.is_answer
        message.save(update_fields=["is_answer"])
        return Response(MessageSerializer(message).data)


class MessagePinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        message = get_object_or_404(
            Message.objects.select_related("channel__section"), pk=pk
        )
        channel = _channel_for_user(request, message.channel_id)
        if not can_moderate_section(request.user, channel.section):
            raise PermissionDenied("Only course moderators can pin messages.")

        message.is_pinned = not message.is_pinned
        message.save(update_fields=["is_pinned"])
        return Response(MessageSerializer(message).data)


class MessageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        message = get_object_or_404(
            Message.objects.select_related("channel__section"), pk=pk
        )
        _channel_for_user(request, message.channel_id)
        if not message.can_be_moderated_by(request.user):
            raise PermissionDenied("You can't delete this message.")

        message.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"results": [], "detail": "Enter at least 2 characters."})

        course_ids = Enrollment.objects.filter(user=request.user).values_list(
            "section__course_id", flat=True
        )
        messages = Message.objects.filter(
            deleted_at__isnull=True, channel__section__course_id__in=course_ids
        ).select_related("channel__section__course", "author__profile")

        if messages.db == "postgresql":
            from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

            search_query = SearchQuery(query, search_type="websearch")
            messages = (
                messages.annotate(rank=SearchRank(SearchVector("body"), search_query))
                .filter(rank__gt=0)
                .order_by("-rank", "-created_at")
            )
        else:
            messages = messages.filter(body__icontains=query).order_by("-created_at")

        results = messages[:50]
        payload = []
        for message in results:
            data = MessageSerializer(message).data
            data["course_code"] = message.channel.section.course.code
            data["channel_name"] = message.channel.name
            payload.append(data)
        return Response({"results": payload})


class AnnouncementView(APIView):
    """Pin an announcement to a section's #general and optionally email the class."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.conf import settings
        from django.core.mail import send_mail

        from courses.models import Section

        section = get_object_or_404(Section.objects.select_related("course"), pk=pk)
        if not can_moderate_section(request.user, section):
            raise PermissionDenied(
                "Only the professor, TAs, or staff can post announcements."
            )

        body = (request.data.get("body") or "").strip()
        if not body:
            raise ValidationError({"body": "Write something to announce."})

        channel = section.channels.filter(name="general").first() or section.channels.first()
        if channel is None:
            return Response(
                {"detail": "This section has no channels."},
                status=status.HTTP_409_CONFLICT,
            )

        message = Message.objects.create(
            channel=channel, author=request.user, body=body, is_pinned=True
        )
        _broadcast(channel.id, message)

        emailed = 0
        if request.data.get("email"):
            emails = (
                Enrollment.objects.filter(section__course=section.course)
                .values_list("user__email", flat=True)
                .distinct()
            )
            for email in emails:
                if not email:
                    continue
                send_mail(
                    subject=f"[{section.course.code}] Announcement",
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                emailed += 1

        return Response(
            {"message": MessageSerializer(message).data, "emailed": emailed},
            status=status.HTTP_201_CREATED,
        )


class ReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = get_object_or_404(Message, pk=serializer.validated_data["message"])
        _channel_for_user(request, message.channel_id)

        Report.objects.get_or_create(
            message=message,
            reporter=request.user,
            defaults={"reason": serializer.validated_data["reason"]},
        )
        return Response(
            {"detail": "Thanks — a moderator will review this."},
            status=status.HTTP_201_CREATED,
        )
