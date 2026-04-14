from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from finances.presentation.urls import core_router, analytics_urls, general_urls
from environment.presentation.http import urlpatterns as health_urls


api_version = settings.RESOLVED_ENV['API_VERSION']
urlpatterns = [
    path('admin/', admin.site.urls),
    path(f'api/{api_version}/', include(core_router.urls)),
    path(f'api/{api_version}/', include(general_urls)),
    path(f'api/{api_version}/analytics/', include(analytics_urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(), name='swagger-ui'),
    *health_urls,
]
