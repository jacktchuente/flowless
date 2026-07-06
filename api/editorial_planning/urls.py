from django.urls import path, include

from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# registration

urlpatterns = [
    path('', include(router.urls))
]
from rest_framework.routers import DefaultRouter

from editorial_planning.views import (
    EditorialChannelCandidateViewSet,
    EditorialFlowRunViewSet,
    EditorialSegmentMembershipViewSet,
    EditorialSegmentViewSet,
)

router = DefaultRouter()
router.register("editorial-flow-run", EditorialFlowRunViewSet, basename="editorial-flow-run")
router.register("editorial-channel-candidate", EditorialChannelCandidateViewSet, basename="editorial-channel-candidate")
router.register("editorial-segment", EditorialSegmentViewSet, basename="editorial-segment")
router.register(
    "editorial-segment-membership",
    EditorialSegmentMembershipViewSet,
    basename="editorial-segment-membership",
)

urlpatterns = router.urls
