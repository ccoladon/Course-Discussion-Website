from django.urls import path

from .views import (
    AnnouncementView,
    ChannelMessageListView,
    ChannelPinnedView,
    MessageAnswerView,
    MessageDeleteView,
    MessagePinView,
    MessageRepliesView,
    ReportCreateView,
    SearchView,
)

urlpatterns = [
    path("channels/<int:pk>/messages/", ChannelMessageListView.as_view(), name="channel-messages"),
    path("channels/<int:pk>/pinned/", ChannelPinnedView.as_view(), name="channel-pinned"),
    path("sections/<int:pk>/announcements/", AnnouncementView.as_view(), name="section-announce"),
    path("messages/<int:pk>/", MessageDeleteView.as_view(), name="message-delete"),
    path("messages/<int:pk>/replies/", MessageRepliesView.as_view(), name="message-replies"),
    path("messages/<int:pk>/answer/", MessageAnswerView.as_view(), name="message-answer"),
    path("messages/<int:pk>/pin/", MessagePinView.as_view(), name="message-pin"),
    path("search/", SearchView.as_view(), name="search"),
    path("reports/", ReportCreateView.as_view(), name="report-create"),
]
