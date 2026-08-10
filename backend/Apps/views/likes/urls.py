from rest_framework.routers import DefaultRouter
from Apps.views.likes.view import LikesViewSet

router = DefaultRouter()
router.register(r'', LikesViewSet, basename='likes')
urlpatterns = router.urls
