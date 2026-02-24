from django.urls import path
from .views import TrialSignupView

urlpatterns = [
    path('signup/trial/', TrialSignupView.as_view(), name='signup-trial'),
]
