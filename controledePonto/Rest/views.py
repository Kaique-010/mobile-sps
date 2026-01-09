from rest_framework import viewsets, status
from rest_framework.decorators import action
from datetime import date, timedelta, datetime
from rest_framework.response import Response
from controledePonto.models import RegistroPonto
from controledePonto.repositorios import RepositorioPontoModelo
from controledePonto.Rest.aplicacoes.casos_uso.pontos_uso import CasosDeUsoPonto
from controledePonto.Rest.serializers import RegistroPontoInputSerializer, RegistroPontoOutputSerializer
from controledePonto.Rest.permissoes import NaoEAdminNemMobile

from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso


class RegistroPontoViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    modulo_necessario = 'controledePonto'
    permission_classes = [NaoEAdminNemMobile]
    queryset = RegistroPonto.objects.none()
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RegistroPontoOutputSerializer
        return RegistroPontoInputSerializer
    
    def _get_banco(self, request) -> str:
        banco = request.query_params.get('banco')
        if banco is None:
            banco = get_licenca_db_config(request)
        return banco
    
    def get_queryset(self):
        banco = self._get_banco(self.request)
        qs = RegistroPonto.objects.using(banco).all().order_by('colaborador_id', 'data_hora')
        colaborador_id = self.request.query_params.get('colaborador_id')
        if colaborador_id:
            qs = qs.filter(colaborador_id=int(colaborador_id))
        return qs
        
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        print(qs)
        serializer = self.get_serializer(qs, many=True)
        print(serializer.data)
        return tratar_sucesso(serializer.data, mensagem='Nenhum registro encontrado' if not qs.exists() else None)
    
    def create(self, request, *args, **kwargs):
        banco = self._get_banco(request)

        serializer = RegistroPontoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uc = CasosDeUsoPonto(RepositorioPontoModelo(banco=banco))
        try:
            registro = uc.registrar_ponto(
                colaborador_id=serializer.validated_data['colaborador_id'],
                tipo=serializer.validated_data['tipo'],
            )
        except ErroDominio as e:
            return tratar_erro(e)

        return tratar_sucesso({
            'id': registro.id,
            'colaborador_id': registro.colaborador_id,
            'documento': registro.documento,
            'data_hora': registro.data_hora,
            'tipo': registro.tipo,
        })

    
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='banco-de-horas')
    def banco_de_horas(self, request, *args, **kwargs):
        banco = self._get_banco(request)
        uc = CasosDeUsoPonto(RepositorioPontoModelo(banco=banco))
        colaborador_id = request.query_params.get('colaborador_id')
        if colaborador_id is None:
            return tratar_erro(ErroDominio('colaborador_id é obrigatório'))
        try:
            colaborador_id = int(colaborador_id)
        except ValueError:
            return tratar_erro(ErroDominio('colaborador_id deve ser um inteiro'))
        data = request.query_params.get('data')
        if data is None:
            return tratar_erro(ErroDominio('data é obrigatória'))
        try:
            data = datetime.strptime(data, '%Y-%m-%d').date()
        except ValueError:
            return tratar_erro(ErroDominio('data deve ser no formato YYYY-MM-DD'))
        try:
            total_trabalhado = uc.total_por_dia(colaborador_id, data)
        except ValueError:
            return tratar_erro(ErroDominio('colaborador_id não existe'))
        try:
            jornada = uc.jornada(colaborador_id)
        except ValueError:
            return tratar_erro(ErroDominio('colaborador_id não existe'))
        banco_de_horas = uc.banco_de_horas(total_trabalhado, jornada)
        return tratar_sucesso({
            'total_trabalhado': str(total_trabalhado),
            'jornada': str(jornada),
            'banco_de_horas': str(banco_de_horas),
        })
        
        
    @action(detail=False, methods=['get'], url_path='total-por-dia')
    def total_por_dia(self, request, *args, **kwargs):
        banco = self._get_banco(request)
        uc = CasosDeUsoPonto(RepositorioPontoModelo(banco=banco))
        colaborador_id = request.query_params.get('colaborador_id')
        if colaborador_id is None:
            return tratar_erro(ErroDominio('colaborador_id é obrigatório'))
        try:
            colaborador_id = int(colaborador_id)
        except ValueError:
            return tratar_erro(ErroDominio('colaborador_id deve ser um inteiro'))
        data = request.query_params.get('data')
        if data is None:
            return tratar_erro(ErroDominio('data é obrigatória'))
        try:
            data = datetime.strptime(data, '%Y-%m-%d').date()
        except ValueError:
            return tratar_erro(ErroDominio('data deve ser no formato YYYY-MM-DD'))
        try:
            total_trabalhado = uc.total_por_dia(colaborador_id, data)
        except ValueError:
            return tratar_erro(ErroDominio('colaborador_id não existe'))
        return tratar_sucesso({
            'total_trabalhado': str(total_trabalhado),
        })