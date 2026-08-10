from rest_framework.routers import DefaultRouter

from Apps.views.campus.view import CampusViewSet

router = DefaultRouter()
router.register(r'', CampusViewSet, basename='campus')
urlpatterns = router.urls
