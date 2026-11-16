from django.urls import path

from .views import GenerateView, Health, ParseResumeView

urlpatterns = [
    path("health/", Health.as_view(), name="health"),
    path("generate/", GenerateView.as_view(), name="generate"),
    path("resumes/parse/", ParseResumeView.as_view(), name="parse-resume"),
]
