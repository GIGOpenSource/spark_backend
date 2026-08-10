from rest_framework.routers import DefaultRouter
from Apps.views.bootstrap.view import BootstrapViewSet

router = DefaultRouter()
router.register(r'', BootstrapViewSet, basename='bootstrap')
urlpatterns = router.urls
