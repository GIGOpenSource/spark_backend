from rest_framework.routers import DefaultRouter

from Apps.views.select.view import SelectViewSet

router = DefaultRouter()
router.register(r'', SelectViewSet, basename='select')
urlpatterns = router.urls
