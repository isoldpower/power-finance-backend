from django.urls import path

from .views import LivenessView, ReadinessView, StartupView

urlpatterns = [
    path("live", LivenessView.as_view(), name="health-live"),
    path("ready", ReadinessView.as_view(), name="health-ready"),
    path("startup", StartupView.as_view(), name="health-startup"),
]
