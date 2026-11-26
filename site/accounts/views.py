from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from courses.models import University

from .models import EmailOTP
from .serializers import ConfirmCodeSerializer, ProfileSerializer, RequestCodeSerializer


def _get_or_create_user(email: str) -> User:
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create_user(username=email, email=email)
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def _apply_university(user: User, email: str) -> bool:
    university = University.for_email(email)
    if university is None:
        return False
    profile = user.profile
    if profile.university_id != university.id or not profile.is_verified:
        profile.university = university
        profile.is_verified = True
        profile.save(update_fields=["university", "is_verified"])
    return True


class RequestCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if not EmailOTP.can_resend(email):
            return Response(
                {"detail": "A code was just sent. Wait a moment before requesting another."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = _get_or_create_user(email)
        verified = _apply_university(user, email)
        _otp, code = EmailOTP.create_for(email, user)

        send_mail(
            subject="Your Course Chat sign-in code",
            message=(
                f"Your sign-in code is {code}. It expires in "
                f"{settings.OTP_TTL_SECONDS // 60} minutes.\n\n"
                "If you didn't request this, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )

        return Response(
            {
                "detail": "Code sent.",
                "verified_domain": verified,
                "dev_code": (
                    code if settings.OTP_DEV_ECHO and settings.DEBUG else None
                ),
                "message": (
                    None
                    if verified
                    else "This email domain isn't linked to a school yet. "
                    "You can sign in, but you can't join courses until it is."
                ),
            }
        )


class ConfirmCodeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        serializer = ConfirmCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        otp = EmailOTP.latest_for(email)
        if otp is None or not otp.verify(code):
            return Response(
                {"detail": "That code is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = otp.user or _get_or_create_user(email)
        _apply_university(user, email)

        # Rotate the token on every login.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {
                "token": token.key,
                "profile": ProfileSerializer(user.profile).data,
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from courses.serializers import EnrollmentSerializer

        profile = request.user.profile
        return Response(
            {
                "profile": ProfileSerializer(profile).data,
                "enrollments": EnrollmentSerializer(
                    request.user.enrollments.select_related(
                        "section__course", "section__professor"
                    ),
                    many=True,
                ).data,
            }
        )

    def patch(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(profile).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
