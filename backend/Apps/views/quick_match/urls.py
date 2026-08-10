from rest_framework.routers import DefaultRouter
from Apps.views.quick_match.view import QuickMatchViewSet

router = DefaultRouter()
router.register(r'', QuickMatchViewSet, basename='quick-match')
urlpatterns = router.urls
