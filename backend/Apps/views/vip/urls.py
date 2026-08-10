from rest_framework.routers import DefaultRouter
from Apps.views.vip.view import VipViewSet

router = DefaultRouter()
router.register(r'', VipViewSet, basename='vip')
urlpatterns = router.urls
