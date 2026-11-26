from django.contrib import admin

from .models import EmailOTP, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("public_name", "user", "university", "role", "is_verified")
    list_filter = ("is_verified", "role", "university")
    search_fields = ("user__email", "display_name")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at", "expires_at", "consumed_at", "attempts")
    list_filter = ("consumed_at",)
    search_fields = ("email",)
    readonly_fields = ("code_hash",)
