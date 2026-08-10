from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Apps.views.verify.view import VerifyViewSet

router = DefaultRouter()
router.register(r'', VerifyViewSet, basename='verify')

urlpatterns = [
    path('', include(router.urls)),
]
