from django.urls import path
from .web_views import DREDashboardView

app_name = "DREWeb"

urlpatterns = [
    path("dashboard/", DREDashboardView.as_view(), name="dre_dashboard"),
]