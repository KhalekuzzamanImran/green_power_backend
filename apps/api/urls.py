from django.urls import path

from . import views


urlpatterns = [
    path("environment/", views.EnvironmentDataView.as_view(), name="environment-data"),
    path("generator/", views.GeneratorDataView.as_view(), name="generator-data"),
    path("grid/realtime/", views.GridRealtimeDataView.as_view(), name="grid-realtime-data"),
    path("grid/energy/", views.GridEnergyDataView.as_view(), name="grid-energy-data"),
    path("solar/", views.SolarDataView.as_view(), name="solar-data"),
]
