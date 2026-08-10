from rest_framework.routers import DefaultRouter

from Apps.views.swipe_night.view import SwipeNightViewSet

router = DefaultRouter()
router.register(r'', SwipeNightViewSet, basename='swipe-night')
urlpatterns = router.urls
