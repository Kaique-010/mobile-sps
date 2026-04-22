from rest_framework.routers import DefaultRouter
from nfse.Rest.views import NfseViewSet

router = DefaultRouter()
router.register(r'nfse', NfseViewSet, basename='nfse')

urlpatterns = router.urls