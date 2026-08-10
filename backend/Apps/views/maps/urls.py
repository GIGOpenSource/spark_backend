from rest_framework.routers import DefaultRouter
from Apps.views.maps.view import MapsViewSet

router = DefaultRouter()
router.register(r'', MapsViewSet, basename='maps')
urlpatterns = router.urls
