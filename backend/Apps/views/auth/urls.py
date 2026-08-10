from rest_framework.routers import DefaultRouter
from Apps.views.auth.view import AuthViewSet

router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')
urlpatterns = router.urls
