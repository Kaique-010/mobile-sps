from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from .models import LogAcao
from .serializers import LogAcaoSerializer
from core.middleware import get_licenca_slug

class IsAdminUser(BasePermission):
    ALLOWED_USERS = ['admin', 'supervisor', 'root']

    def has_permission(self, request, view):
        user = request.user
        if not user or not hasattr(user, 'usua_nome'):
            return False
        return user.usua_nome in self.ALLOWED_USERS

class LogAcaoFilter(django_filters.FilterSet):
    data_inicio = django_filters.DateFilter(field_name='data_hora', lookup_expr='gte')
    data_fim = django_filters.DateFilter(field_name='data_hora', lookup_expr='lte')
    metodo = django_filters.CharFilter(field_name='tipo_acao', lookup_expr='icontains')
    usuario = django_filters.CharFilter(field_name='usuario__usua_nome', lookup_expr='icontains')

    class Meta:
        model = LogAcao
        fields = {
            'empresa': ['exact', 'in'],
            'licenca': ['exact'],
            'url': ['icontains'],
            'tipo_acao': ['icontains'],
            'usuario': ['exact'],
        }

class LogAcaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LogAcaoSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = LogAcaoFilter
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ['url', 'dados', 'navegador']
    ordering_fields = ['data_hora', 'tipo_acao', 'usuario__usua_nome', 'empresa', 'licenca']
    ordering = ['-data_hora']

    def get_queryset(self, slug=None):
        
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        # Para admin: devolve tudo
        if self.action == 'admin':
            return LogAcao.objects.all()

        # Para usuário comum: filtra pelo slug da licença
        licenca_slug = get_licenca_slug(self.request)
        if not licenca_slug:
            return LogAcao.objects.none()
        return LogAcao.objects.filter(licenca=licenca_slug)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def admin(self, request, slug= None):
        
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        queryset = self.filter_queryset(self.get_queryset(slug))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
