from rest_framework.routers import DefaultRouter
from Apps.views.translate.view import TranslateViewSet

router = DefaultRouter()
router.register(r'', TranslateViewSet, basename='translate')
urlpatterns = router.urls
