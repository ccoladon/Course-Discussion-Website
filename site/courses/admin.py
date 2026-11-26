from django.contrib import admin

from .models import Course, CourseAlias, Enrollment, Section, University


class CourseAliasInline(admin.TabularInline):
    model = CourseAlias
    extra = 1


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ("professor", "term", "section_code", "is_default")


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "email_domains")
    search_fields = ("name", "email_domains")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "university", "created_at")
    list_filter = ("university",)
    search_fields = ("code", "title")
    inlines = [CourseAliasInline, SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "course",
        "professor",
        "term",
        "section_code",
        "is_default",
        "claim_pending",
    )
    list_filter = ("term", "is_default", "claim_pending", "course__university")
    search_fields = ("course__code", "course__title")
    actions = ["approve_claims"]

    @admin.action(description="Approve pending professor claims")
    def approve_claims(self, request, queryset):
        approved = 0
        for section in queryset.filter(claim_pending=True, claimed_by__isnull=False):
            profile = section.claimed_by
            section.professor = profile
            section.claim_pending = False
            section.save(update_fields=["professor", "claim_pending"])
            Enrollment.objects.update_or_create(
                user=profile.user,
                section=section,
                defaults={"role": Enrollment.ROLE_PROFESSOR},
            )
            profile.role = profile.ROLE_PROFESSOR
            profile.save(update_fields=["role"])
            approved += 1
        self.message_user(request, f"Approved {approved} professor claim(s).")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "section", "role", "joined_at")
    list_filter = ("role", "section__course__university")
    search_fields = ("user__email", "nickname")
