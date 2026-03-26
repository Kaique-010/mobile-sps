from django.urls import path, include
from rest_framework.routers import DefaultRouter
from transportes.views import api

router = DefaultRouter()
router.register(r'ctes', api.CteViewSet, basename='api-cte')
router.register(r'mdfes', api.MdfeViewSet, basename='api-mdfe')

urlpatterns = [
    path('', include(router.urls)),
]
