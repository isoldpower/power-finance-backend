from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .http.base_api_view import BaseAPIView


class AsyncSpectacularAPIView(BaseAPIView, SpectacularAPIView):
    view_is_async = True


class AsyncSpectacularSwaggerView(BaseAPIView, SpectacularSwaggerView):
    view_is_async = True