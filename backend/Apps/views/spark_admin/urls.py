from rest_framework.routers import DefaultRouter
from Apps.views.spark_admin.view import SparkAdminViewSet

router = DefaultRouter()
router.register(r'', SparkAdminViewSet, basename='spark-admin')
urlpatterns = router.urls
