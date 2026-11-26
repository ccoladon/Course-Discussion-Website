"""WebSocket consumer for live course chat."""

from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from courses.models import Enrollment

from .models import Channel, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.channel_id = int(self.scope["url_route"]["kwargs"]["channel_id"])
        self.group_name = f"channel_{self.channel_id}"

        if not await self._can_access(self.channel_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type", "message")

        if event_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if event_type != "message":
            return

        body = (content.get("body") or "").strip()
        if not body:
            await self.send_json({"type": "error", "detail": "Message body is required."})
            return

        parent_id = content.get("parent")
        payload = await self._create_message(self.channel_id, body, parent_id)
        if payload is None:
            await self.send_json({"type": "error", "detail": "Could not post message."})
            return

        await self.channel_layer.group_send(
            self.group_name, {"type": "chat.message", "message": payload}
        )

    async def chat_message(self, event):
        await self.send_json({"type": "message", "message": event["message"]})

    # -- database helpers -------------------------------------------------

    @database_sync_to_async
    def _can_access(self, channel_id: int) -> bool:
        try:
            channel = Channel.objects.select_related("section").get(pk=channel_id)
        except Channel.DoesNotExist:
            return False
        return Enrollment.objects.filter(
            user=self.user, section__course_id=channel.section.course_id
        ).exists()

    @database_sync_to_async
    def _create_message(self, channel_id: int, body: str, parent_id):
        try:
            channel = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist:
            return None

        parent = None
        if parent_id:
            parent = Message.objects.filter(
                pk=parent_id, channel=channel, parent__isnull=True
            ).first()

        message = Message.objects.create(
            channel=channel, author=self.user, body=body, parent=parent
        )
        return {
            "id": message.id,
            "body": message.body,
            "channel": channel.id,
            "parent": parent.id if parent else None,
            "author": {
                "id": self.user.id,
                "name": getattr(getattr(self.user, "profile", None), "public_name", None)
                or self.user.username,
            },
            "is_answer": False,
            "is_pinned": False,
            "created_at": timezone.localtime(message.created_at).isoformat(),
        }
