from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("courses.urls")),
    path("api/", include("chat.urls")),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("app/", TemplateView.as_view(template_name="app.html"), name="app"),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
]
