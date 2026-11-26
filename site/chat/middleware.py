"""WebSocket authentication middleware.

Session auth is handled by Channels' ``AuthMiddlewareStack``; mobile clients
authenticate with a DRF token passed as ``?token=<key>``.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async


@database_sync_to_async
def _user_for_token(key: str):
    from rest_framework.authtoken.models import Token

    token = Token.objects.select_related("user").filter(key=key).first()
    return token.user if token else None


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if token:
            user = await _user_for_token(token)
            if user is not None:
                scope = dict(scope)
                scope["user"] = user
        return await self.inner(scope, receive, send)
