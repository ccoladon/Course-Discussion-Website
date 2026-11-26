from django.urls import path

from .views import ConfirmCodeView, LogoutView, MeView, RequestCodeView

urlpatterns = [
    path("auth/request-code/", RequestCodeView.as_view(), name="auth-request-code"),
    path("auth/confirm-code/", ConfirmCodeView.as_view(), name="auth-confirm-code"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="me"),
]
