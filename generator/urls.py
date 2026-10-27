from django.urls import path

from .views import GenerateView, Health

urlpatterns = [
    path("health/", Health.as_view(), name="health"),
    path("generate/", GenerateView.as_view(), name="generate"),
]
