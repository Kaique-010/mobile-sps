from django.urls import path
from .views import TrialSignupView
from planos.authentication import TrialAwareTokenObtainPairView

urlpatterns = [
    path('signup/trial/', TrialSignupView.as_view(), name='signup-trial'),
    path('token/', TrialAwareTokenObtainPairView.as_view(), name='token'),
   ]
