import os

from rest_framework import serializers

MESSAGE_TYPE = ["connection_note", "inmail", "follow_up"]
MESSAGE_TONE = ["friendly", "formal", "brief"]
ALLOWED_EXTENSIONS = {".txt", ".docx"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


class GenerateRequestSerializer(serializers.Serializer):
    resume = serializers.FileField()
    company = serializers.CharField(max_length=100)
    recruiter_name = serializers.CharField(max_length=100)
    job_text = serializers.CharField(max_length=5000)
    message_type = serializers.ChoiceField(choices=MESSAGE_TYPE)
    tone = serializers.ChoiceField(choices=MESSAGE_TONE)

    def validate_resume(self, resume):
        ext = os.path.splitext(resume.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Only .txt and .docx files are allowed.")

        if resume.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("File is too large (max 2 MB).")
        return resume
