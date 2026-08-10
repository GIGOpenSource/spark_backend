from rest_framework.routers import DefaultRouter
from Apps.views.chat.view import ChatViewSet

router = DefaultRouter()
router.register(r'', ChatViewSet, basename='chat')
urlpatterns = router.urls
