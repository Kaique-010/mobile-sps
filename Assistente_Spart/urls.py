from django.urls import path
from .views import SpartView

urlpatterns = [
    path('chat/', SpartView.as_view(), name='chat'),
]
