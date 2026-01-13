from django.urls import path
from . import views
from .auth import RoleTokenObtainPairView, RoleTokenRefreshView, RoleTokenVerifyView


urlpatterns = [
    path("auth/token/", RoleTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", RoleTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", RoleTokenVerifyView.as_view(), name="token-verify"),
    path("environment/", views.EnvironmentDataView.as_view(), name="environment-data"),
    path("generator/", views.GeneratorDataView.as_view(), name="generator-data"),
    path("grid/realtime/", views.GridRealtimeDataView.as_view(), name="grid-realtime-data"),
    path("grid/energy/", views.GridEnergyDataView.as_view(), name="grid-energy-data"),
    path("solar/", views.SolarDataView.as_view(), name="solar-data"),
]
