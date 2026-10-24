from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


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
