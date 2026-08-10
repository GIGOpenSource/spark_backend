from rest_framework.routers import DefaultRouter
from Apps.views.match.view import MatchViewSet

router = DefaultRouter()
router.register(r'', MatchViewSet, basename='match')
urlpatterns = router.urls
