from django.urls import path
from . import views

urlpatterns = [
    path("", views.weather, name='weather'),
    path("history/", views.weather_history, name='history'),
    path('export/', views.export_weather_csv, name='export_weather_csv'),
    path('health/', views.health_check, name='health_check'),
]
