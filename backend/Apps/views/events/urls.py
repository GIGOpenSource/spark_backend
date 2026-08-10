from rest_framework.routers import DefaultRouter
from Apps.views.events.view import EventsViewSet

router = DefaultRouter()
router.register(r'', EventsViewSet, basename='events')
urlpatterns = router.urls
