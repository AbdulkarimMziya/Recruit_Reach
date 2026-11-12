from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import AIServiceError, UnreadableResumeError
from .schemas import ResumeData
from .serializers import (
    GenerateRequestSerializer,
    GenerateResponseSerializer,
    ParseRequestSerializer,
)
from .services.generator import generate_message
from .services.parser import parse_resume
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
    @extend_schema(
        summary="Generate a LinkedIn message to a recruiter",
        description="Upload a resume (.txt, .docx or .pdf) and paste a job post. "
        "The AI picks your most relevant projects and writes a short message.",
        request={"multipart/form-data": GenerateRequestSerializer},
        responses={
            200: GenerateResponseSerializer,
            400: OpenApiResponse(description="Invalid input, or the resume couldn't be read."),
            503: OpenApiResponse(description="The AI service is unavailable. Try again shortly."),
        },
    )
    def post(self, request):
        serializer = GenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            resume_text = extract_text(data["resume"])

            company = data["company"]
            recruiter_name = data["recruiter_name"]
            job_text = data["job_text"]
            message_type = data["message_type"]
            tone = data["tone"]

            message = generate_message(
                resume_text=resume_text,
                company=company,
                recruiter_name=recruiter_name,
                job_text=job_text,
                message_type=message_type,
                tone=tone,
            )

        except UnreadableResumeError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except AIServiceError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"message": message, "message_type": message_type, "char_count": len(message)}
        )


class ParseResumeView(APIView):
    @extend_schema(
        summary="Sort a resume into sections",
        description="Upload a resume (.txt, .docx or .pdf). The AI sorts it into "
        "experience, projects, education, skills and certifications, copying "
        "every bullet word for word.",
        request={"multipart/form-data": ParseRequestSerializer},
        responses={
            200: ResumeData,
            400: OpenApiResponse(description="Invalid file, or the resume couldn't be read."),
            503: OpenApiResponse(
                description="The AI service is unavailable, or its answer was invalid."
            ),
        },
    )
    def post(self, request):
        serializer = ParseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            text = extract_text(serializer.validated_data["resume"])
            resume = parse_resume(text)
        except UnreadableResumeError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except AIServiceError as e:
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(resume.model_dump())
