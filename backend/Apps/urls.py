#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework import routers

from Apps.views.user.view import UserViewSet, AdminUserViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', include('Apps.views.admin.urls')),
    path('example/', include('Apps.views.Example.urls')),
    # Spark product APIs
    path('bootstrap/', include('Apps.views.bootstrap.urls')),
    path('auth/', include('Apps.views.auth.urls')),
    path('recommend/', include('Apps.views.recommend.urls')),
    path('likes/', include('Apps.views.likes.urls')),
    path('profile/', include('Apps.views.profile.urls')),
    path('match/', include('Apps.views.match.urls')),
    path('chat/', include('Apps.views.chat.urls')),
    path('vip/', include('Apps.views.vip.urls')),
    path('translate/', include('Apps.views.translate.urls')),
    path('maps/', include('Apps.views.maps.urls')),
    path('events/', include('Apps.views.events.urls')),
    path('push/', include('Apps.views.push.urls')),
    path('verify/', include('Apps.views.verify.urls')),
    path('safety/', include('Apps.views.safety.urls')),
    path('swipe-night/', include('Apps.views.swipe_night.urls')),
    path('matchmaker/', include('Apps.views.matchmaker.urls')),
    path('campus/', include('Apps.views.campus.urls')),
    path('select/', include('Apps.views.select.urls')),
    path('face-to-face/', include('Apps.views.face_to_face.urls')),
    path('quick-match/', include('Apps.views.quick_match.urls')),
    path('group/', include('Apps.views.group.urls')),
    path('community/', include('Apps.views.community.urls')),
    path('moments/', include('Apps.views.moments.urls')),
    path('videos/', include('Apps.views.videos.urls')),
    path('spark-admin/', include('Apps.views.spark_admin.urls')),
]
