from django.urls import path
from dashboard.views import DashboardOverviewView

urlpatterns = [
    path(
        "dashboard/overview/",
        DashboardOverviewView.as_view(),
        name="dashboard-overview",
    )
]
