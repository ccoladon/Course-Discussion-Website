"""Helpers for building authenticated fixtures in tests."""

from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


def make_user(email: str, university=None, verified: bool = True) -> User:
    user = User.objects.create_user(username=email, email=email)
    profile = user.profile
    if university is not None:
        profile.university = university
    profile.is_verified = verified
    profile.save()
    return user


def auth_client(user: User) -> APIClient:
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client
