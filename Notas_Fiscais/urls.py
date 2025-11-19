from django.urls import path, include

urlpatterns = [
    path("notas-fiscais/", include("Notas_Fiscais.REST.urls")),
    
]