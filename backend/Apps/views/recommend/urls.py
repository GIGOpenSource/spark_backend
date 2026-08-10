from rest_framework.routers import DefaultRouter
from Apps.views.recommend.view import RecommendViewSet

router = DefaultRouter()
router.register(r'', RecommendViewSet, basename='recommend')
urlpatterns = router.urls
