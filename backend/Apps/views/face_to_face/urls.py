from rest_framework.routers import DefaultRouter

from Apps.views.face_to_face.view import FaceToFaceViewSet

router = DefaultRouter()
router.register(r'', FaceToFaceViewSet, basename='face-to-face')
urlpatterns = router.urls
