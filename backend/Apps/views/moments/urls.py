from rest_framework.routers import DefaultRouter
from Apps.views.moments.view import MomentsViewSet

router = DefaultRouter()
router.register(r'', MomentsViewSet, basename='moments')
urlpatterns = router.urls
