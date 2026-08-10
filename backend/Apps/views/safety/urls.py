from rest_framework.routers import DefaultRouter

from Apps.views.safety.view import SafetyViewSet

router = DefaultRouter()
router.register(r'', SafetyViewSet, basename='safety')
urlpatterns = router.urls
