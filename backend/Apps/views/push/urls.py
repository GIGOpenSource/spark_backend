from rest_framework.routers import DefaultRouter
from Apps.views.push.view import PushViewSet

router = DefaultRouter()
router.register(r'', PushViewSet, basename='push')
urlpatterns = router.urls
