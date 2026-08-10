from rest_framework.routers import DefaultRouter

from Apps.views.matchmaker.view import MatchmakerViewSet

router = DefaultRouter()
router.register(r'', MatchmakerViewSet, basename='matchmaker')
urlpatterns = router.urls
