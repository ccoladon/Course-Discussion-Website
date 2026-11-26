from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.serializers import ChannelSerializer
from core.text import normalize_course_code

from .models import Course, Enrollment, Section
from .permissions import can_moderate_section, is_enrolled_in_course
from .serializers import CourseSerializer, EnrollmentSerializer, SectionSerializer


class CourseSearchView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Course.objects.select_related("university").prefetch_related("aliases")
        qs = qs.annotate(section_count=Count("sections", distinct=True))

        query = self.request.query_params.get("q", "").strip()
        if query:
            normalized = normalize_course_code(query)
            qs = qs.filter(
                Q(code__icontains=normalized)
                | Q(code__icontains=query)
                | Q(title__icontains=query)
                | Q(aliases__alias__icontains=query)
            ).distinct()

        university = self.request.query_params.get("university")
        if university:
            qs = qs.filter(university__slug=university)

        return qs.order_by("code")


class CourseCreateView(generics.CreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        profile = request.user.profile
        if not profile.is_verified or profile.university_id is None:
            raise PermissionDenied(
                "Verify a school email domain before creating a course."
            )

        code = normalize_course_code(request.data.get("code", ""))
        title = (request.data.get("title") or "").strip()
        if not code or not title:
            raise ValidationError({"detail": "Both a course code and title are required."})

        if Course.objects.filter(university=profile.university, code=code).exists():
            raise ValidationError({"code": f"{code} already exists at your school."})

        course = Course.objects.create(
            university=profile.university,
            code=code,
            title=title,
            description=request.data.get("description", ""),
        )

        section = course.default_section
        Enrollment.objects.get_or_create(user=request.user, section=section)

        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Course.objects.select_related("university").prefetch_related("aliases")


class JoinCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        profile = request.user.profile
        if not profile.is_verified:
            raise PermissionDenied("Your school email hasn't been verified yet.")

        course = Course.objects.filter(pk=pk).first()
        if course is None:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

        section_id = request.data.get("section_id")
        if section_id:
            section = Section.objects.filter(pk=section_id, course=course).first()
            if section is None:
                raise ValidationError({"section_id": "That section isn't part of this course."})
        else:
            section = course.default_section

        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user, section=section
        )
        return Response(
            EnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MySectionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        course_ids = request.user.enrollments.values_list(
            "section__course_id", flat=True
        ).distinct()
        sections = (
            Section.objects.filter(course_id__in=course_ids)
            .select_related("course", "course__university", "professor")
            .prefetch_related("channels")
            .order_by("course__code", "-is_default", "section_code")
        )
        my_enrollments = {
            enrollment.section_id: enrollment
            for enrollment in request.user.enrollments.all()
        }

        payload = []
        for section in sections:
            enrollment = my_enrollments.get(section.id)
            payload.append(
                {
                    "section": SectionSerializer(section).data,
                    "channels": ChannelSerializer(section.channels.all(), many=True).data,
                    "can_moderate": can_moderate_section(request.user, section),
                    "my_enrollment": (
                        EnrollmentSerializer(enrollment).data if enrollment else None
                    ),
                }
            )
        return Response({"sections": payload})


class SectionChannelsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        section = Section.objects.filter(pk=pk).select_related("course").first()
        if section is None:
            return Response({"detail": "Section not found."}, status=status.HTTP_404_NOT_FOUND)
        if not is_enrolled_in_course(request.user, section.course_id):
            raise PermissionDenied("Join this course first.")

        channels = section.channels.all()
        return Response(
            {
                "section": SectionSerializer(section).data,
                "channels": ChannelSerializer(channels, many=True).data,
            }
        )


class ClaimProfessorView(APIView):
    """Request to be recognized as a section's professor.

    Claims are reviewed in Django admin. Until approved, the claimant gets no
    moderation powers, so a student can't impersonate a professor.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        section = Section.objects.filter(pk=pk).select_related("course").first()
        if section is None:
            return Response({"detail": "Section not found."}, status=status.HTTP_404_NOT_FOUND)
        if section.professor_id is not None:
            raise ValidationError({"detail": "This section already has a professor."})
        if section.claim_pending:
            raise ValidationError({"detail": "A claim for this section is already pending."})

        profile = request.user.profile
        if not profile.is_verified:
            raise PermissionDenied("Verify your school email before claiming a section.")
        if profile.university_id != section.course.university_id:
            raise PermissionDenied("You can only claim sections at your own school.")

        section.claimed_by = profile
        section.claim_pending = True
        section.save(update_fields=["claimed_by", "claim_pending"])

        return Response(
            {"detail": "Claim submitted. An administrator will review it."},
            status=status.HTTP_202_ACCEPTED,
        )
