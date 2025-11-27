from django.urls import path
from .Views import list, delete, update, create

urlpatterns = [
    path('', list.SeriesListView.as_view(), name='series-list'),
    path('create/', create.SeriesCreateView.as_view(), name='series-create'),

    path('<int:seri_empr>/<str:seri_codi>/edit/', update.SeriesUpdateView.as_view(), name='series-update'),
    path('<int:seri_empr>/<str:seri_codi>/delete/', delete.SeriesDeleteView.as_view(), name='series-delete'),
]
