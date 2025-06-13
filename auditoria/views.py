from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.http import HttpResponse
from datetime import datetime, timedelta
from django.utils import timezone
from .models import LogAcao
from .serializers import LogAcaoSerializer
from .utils import (
    gerar_relatorio_atividades,
    buscar_alteracoes_objeto,
    detectar_atividades_suspeitas,
    exportar_logs_csv,
    obter_estatisticas_rapidas,
    comparar_objetos_detalhado
)
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

    def get_queryset(self):
        queryset = LogAcao.objects.all()
        licenca = get_licenca_slug()
        if licenca:
            queryset = queryset.filter(licenca=licenca)
        return queryset.order_by('-data_hora')
    
    @action(detail=False, methods=['get'])
    def relatorio_atividades(self, request):
        """
        Gera relatório de atividades com estatísticas
        Parâmetros: data_inicio, data_fim, usuario_id
        """
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        usuario_id = request.query_params.get('usuario_id')
        
        # Converter strings de data
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            except ValueError:
                return Response(
                    {'erro': 'Formato de data_inicio inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                # Incluir o dia inteiro
                data_fim = data_fim.replace(hour=23, minute=59, second=59)
            except ValueError:
                return Response(
                    {'erro': 'Formato de data_fim inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        usuario = None
        if usuario_id:
            try:
                from core.models import Usuario
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                return Response(
                    {'erro': 'Usuário não encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        licenca = get_licenca_slug()
        relatorio = gerar_relatorio_atividades(
            data_inicio=data_inicio,
            data_fim=data_fim,
            usuario=usuario,
            empresa=licenca
        )
        
        return Response(relatorio)
    
    @action(detail=False, methods=['get'])
    def historico_objeto(self, request):
        """
        Busca histórico completo de alterações de um objeto
        Parâmetros obrigatórios: modelo, objeto_id
        """
        modelo = request.query_params.get('modelo')
        objeto_id = request.query_params.get('objeto_id')
        
        if not modelo or not objeto_id:
            return Response(
                {'erro': 'Parâmetros modelo e objeto_id são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        historico = buscar_alteracoes_objeto(modelo, objeto_id)
        
        return Response({
            'modelo': modelo,
            'objeto_id': objeto_id,
            'total_alteracoes': len(historico),
            'historico': historico
        })
    
    @action(detail=False, methods=['get'])
    def atividades_suspeitas(self, request):
        """
        Detecta atividades potencialmente suspeitas
        Parâmetro opcional: dias (padrão: 7)
        """
        dias = request.query_params.get('dias', 7)
        try:
            dias = int(dias)
        except ValueError:
            return Response(
                {'erro': 'Parâmetro dias deve ser um número'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suspeitas = detectar_atividades_suspeitas(dias=dias)
        
        return Response({
            'periodo_analisado': f'{dias} dias',
            'total_suspeitas': len(suspeitas),
            'suspeitas': suspeitas
        })
    
    @action(detail=False, methods=['get'])
    def estatisticas(self, request):
        """
        Obtém estatísticas rápidas para dashboard
        """
        licenca = get_licenca_slug()
        stats = obter_estatisticas_rapidas(licenca=licenca)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def exportar_csv(self, request):
        """
        Exporta logs filtrados para CSV
        Parâmetros opcionais: data_inicio, data_fim, usuario_id, tipo_acao
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Aplicar filtros adicionais
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        usuario_id = request.query_params.get('usuario_id')
        tipo_acao = request.query_params.get('tipo_acao')
        
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                queryset = queryset.filter(data_hora__gte=data_inicio)
            except ValueError:
                return Response(
                    {'erro': 'Formato de data_inicio inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                data_fim = data_fim.replace(hour=23, minute=59, second=59)
                queryset = queryset.filter(data_hora__lte=data_fim)
            except ValueError:
                return Response(
                    {'erro': 'Formato de data_fim inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        
        if tipo_acao:
            queryset = queryset.filter(tipo_acao=tipo_acao)
        
        # Limitar a 10000 registros para evitar sobrecarga
        if queryset.count() > 10000:
            return Response(
                {'erro': 'Muitos registros para exportação. Use filtros mais específicos.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        csv_content = exportar_logs_csv(queryset)
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="logs_auditoria_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        return response
    
    @action(detail=False, methods=['get'])
    def comparar_objeto(self, request):
        """
        Compara o estado de um objeto entre duas datas
        Parâmetros obrigatórios: modelo, objeto_id, data_inicio, data_fim
        """
        modelo = request.query_params.get('modelo')
        objeto_id = request.query_params.get('objeto_id')
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        if not all([modelo, objeto_id, data_inicio, data_fim]):
            return Response(
                {'erro': 'Parâmetros modelo, objeto_id, data_inicio e data_fim são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim = data_fim.replace(hour=23, minute=59, second=59)
        except ValueError:
            return Response(
                {'erro': 'Formato de data inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comparacao = comparar_objetos_detalhado(
            modelo, objeto_id, data_inicio, data_fim
        )
        
        if comparacao is None:
            return Response(
                {'erro': 'Nenhum log encontrado para o objeto no período especificado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(comparacao)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def admin(self, request, slug= None):
        
        slug = get_licenca_slug()

        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
