from rest_framework.routers import DefaultRouter
from Apps.views.community.view import CommunityViewSet

router = DefaultRouter()
router.register(r'', CommunityViewSet, basename='community')
urlpatterns = router.urls
