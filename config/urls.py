from django.urls import path, include
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.realtime.views import index
from config.admin_site import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', index),
    path('api/', include('apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema', permission_classes=[AllowAny]), name='api-docs'),
]
