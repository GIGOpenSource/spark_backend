from rest_framework.routers import DefaultRouter
from Apps.views.group.view import GroupViewSet

router = DefaultRouter()
router.register(r'', GroupViewSet, basename='group')
urlpatterns = router.urls
