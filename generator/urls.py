from django.urls import path

from .views import Health

urlpatterns = [
    path('health/', Health.as_view(), name="health")
]