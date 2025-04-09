from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from .models import Produtos
from .serializers import ProdutoSerializer

class ProdutoListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        produtos = Produtos.objects.all()
        serializer = ProdutoSerializer(produtos, many=True)
        return Response(serializer.data)


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produtos.objects.all()
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ['prod_nome', 'prod_codi']
    
    def perform_create(self, serializer):
        
        serializer.save()