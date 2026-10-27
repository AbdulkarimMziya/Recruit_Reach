from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import UnreadableResumeError
from .serializers import GenerateRequestSerializer
from .services.resume import extract_text


# Create your views here.
class Health(APIView):
    @extend_schema(
        summary="Health check",
        responses={
            200: inline_serializer(
                name="HealthResponse",
                fields={"status": serializers.CharField()},
            ),
        },
    )
    def get(self, request):
        return Response(
            {"status": "ok"},
            status=status.HTTP_200_OK,
        )


class GenerateView(APIView):
    def post(self, request):
        serializer = GenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            text = extract_text(data["resume"])
        except UnreadableResumeError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"resume_chars": len(text)})
