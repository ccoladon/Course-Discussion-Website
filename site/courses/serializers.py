from rest_framework import serializers

from .models import Course, Enrollment, Section, University


class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "slug"]


class CourseSerializer(serializers.ModelSerializer):
    university = UniversitySerializer(read_only=True)
    aliases = serializers.SlugRelatedField(slug_field="alias", many=True, read_only=True)
    section_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "slug",
            "description",
            "university",
            "aliases",
            "section_count",
        ]

    def get_section_count(self, obj):
        return getattr(obj, "section_count", obj.sections.count())


class SectionSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    professor = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = [
            "id",
            "course",
            "professor",
            "term",
            "section_code",
            "is_default",
            "display_name",
        ]

    def get_professor(self, obj):
        if obj.professor is None:
            return None
        return {"id": obj.professor.id, "name": obj.professor.public_name}


class EnrollmentSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)
    course_code = serializers.CharField(source="section.course.code", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "section", "course_code", "role", "nickname", "joined_at"]
