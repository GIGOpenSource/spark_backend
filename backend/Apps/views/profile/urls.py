from rest_framework.routers import DefaultRouter
from Apps.views.profile.view import ProfileViewSet

router = DefaultRouter()
router.register(r'', ProfileViewSet, basename='profile')
urlpatterns = router.urls
