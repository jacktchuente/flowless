from django.urls import path, include
from rest_framework.routers import DefaultRouter

from grid_schedule.views.scheduler_views import SchedulerViewSet

router = DefaultRouter()
router.register('scheduler', SchedulerViewSet, basename='scheduler')

# registration

urlpatterns = [
    path('', include(router.urls))
]
