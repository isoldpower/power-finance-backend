from django.urls import path

from .views import LivenessView, ReadinessView, StartupView
from ..spectacular_async import AsyncSpectacularAPIView, AsyncSpectacularSwaggerView


health_urls = [
    path('health/live', LivenessView.as_view(), name='health-live'),
    path('health/ready', ReadinessView.as_view(), name='health-ready'),
    path('health/startup', StartupView.as_view(), name='health-startup'),
]

docs_urls = [
    path('api/schema/', AsyncSpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', AsyncSpectacularSwaggerView.as_view(), name='swagger-ui'),
]
