from django.urls import path

from .views import (
    ClaimProfessorView,
    CourseCreateView,
    CourseDetailView,
    CourseSearchView,
    JoinCourseView,
    MySectionsView,
    SectionChannelsView,
)

urlpatterns = [
    path("courses/", CourseCreateView.as_view(), name="course-create"),
    path("courses/search/", CourseSearchView.as_view(), name="course-search"),
    path("courses/<int:pk>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:pk>/join/", JoinCourseView.as_view(), name="course-join"),
    path("me/sections/", MySectionsView.as_view(), name="my-sections"),
    path("sections/<int:pk>/channels/", SectionChannelsView.as_view(), name="section-channels"),
    path("sections/<int:pk>/claim/", ClaimProfessorView.as_view(), name="section-claim"),
]
