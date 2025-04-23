# urls.py
from rest_framework.routers import DefaultRouter
from .views import EntidadesViewSet

router = DefaultRouter()
router.register(r'entidades', EntidadesViewSet, basename='entidades')

urlpatterns = router.urls
