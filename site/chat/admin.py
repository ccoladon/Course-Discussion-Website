from django.contrib import admin

from .models import Channel, Message, Reaction, Report


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "kind")
    list_filter = ("kind",)
    search_fields = ("name", "section__course__code")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "author", "is_answer", "is_pinned", "created_at")
    list_filter = ("is_answer", "is_pinned", "deleted_at")
    search_fields = ("body", "author__email")
    raw_id_fields = ("parent", "channel")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("message", "reporter", "reason", "status", "created_at")
    list_filter = ("status",)
    actions = ["mark_reviewed", "mark_dismissed"]

    @admin.action(description="Mark selected reports reviewed")
    def mark_reviewed(self, request, queryset):
        queryset.update(status=Report.STATUS_REVIEWED)

    @admin.action(description="Dismiss selected reports")
    def mark_dismissed(self, request, queryset):
        queryset.update(status=Report.STATUS_DISMISSED)


admin.site.register(Reaction)
