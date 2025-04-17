# dashboards/urls.py
from django.urls import path
from .views import DashboardAPIView

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard_api'),
]
