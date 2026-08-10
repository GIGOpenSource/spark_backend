from rest_framework.routers import DefaultRouter
from Apps.views.videos.view import VideosViewSet

router = DefaultRouter()
router.register(r'', VideosViewSet, basename='videos')
urlpatterns = router.urls
