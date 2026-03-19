from datetime import datetime

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import Lctobancario
from rest_framework.permissions import IsAuthenticated
from .serializers import LctobancarioSerializer
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from core.utils import get_licenca_db_config
from .services import obter_resumo_dashboard

import logging

logger = logging.getLogger(__name__)


class LctobancarioViewSet(ModuloRequeridoMixin, viewsets.ModelViewSet):
    serializer_class = LctobancarioSerializer
    modulo_necessario = 'Financeiro'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['laba_empr', 'laba_fili', 'laba_ctrl']
    search_fields = ['laba_data', 'laba_ctrl']
    
    def get_queryset(self):
        banco = get_licenca_db_config(self.request)
        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
        
        queryset = Lctobancario.objects.using(banco).all().order_by('laba_data')
        logger.info(f"Lctobancario carregados")
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context
    
    def destroy(self, request, *args, **kwargs):
        """Override para adicionar validações antes da exclusão"""
        lctobancario = self.get_object()
        banco = get_licenca_db_config(self.request)

        if not banco:
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")

        # Aqui você pode adicionar validações específicas antes da exclusão
        # Por exemplo, verificar se há registros dependentes
        
        logger.info(f"🗑️ Exclusão do lctobancario {lctobancario.laba_ctrl} iniciada")
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"🗑️ Exclusão do lctobancario concluída")
        
        return response

    @action(detail=False, methods=["get"])
    def dashboard(self, request, slug=None):
        banco = get_licenca_db_config(request)
        if not banco:
            raise NotFound("Banco de dados não encontrado.")

        empresa_id = (
            request.query_params.get("empresa_id")
            or request.headers.get("X-Empresa")
            or request.session.get("empresa_id")
            or request.query_params.get("empr")
        )
        filial_id = (
            request.query_params.get("filial_id")
            or request.headers.get("X-Filial")
            or request.session.get("filial_id")
            or request.query_params.get("fili")
        )
        centro_custo_id = (
            request.query_params.get("centro_custo")
            or request.query_params.get("cecu")
            or request.query_params.get("cc")
            or request.query_params.get("centrodecusto")
        )
        data_inicial = request.query_params.get("data_ini")
        data_final = request.query_params.get("data_fim")
        limite = request.query_params.get("limite") or 10

        try:
            empresa_id = int(empresa_id) if empresa_id is not None else None
        except Exception:
            empresa_id = None
        try:
            filial_id = int(filial_id) if filial_id is not None else None
        except Exception:
            filial_id = None
        try:
            centro_custo_id_int = int(centro_custo_id) if centro_custo_id not in (None, "") else None
        except Exception:
            centro_custo_id_int = None

        try:
            data_inicial_dt = datetime.strptime(data_inicial, "%Y-%m-%d").date() if data_inicial else None
        except Exception:
            data_inicial_dt = None
        try:
            data_final_dt = datetime.strptime(data_final, "%Y-%m-%d").date() if data_final else None
        except Exception:
            data_final_dt = None

        try:
            limite_int = max(1, min(int(limite), 100))
        except Exception:
            limite_int = 10

        return Response(
            obter_resumo_dashboard(
                banco=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                centro_custo_id=centro_custo_id_int,
                data_inicial=data_inicial_dt,
                data_final=data_final_dt,
                limite=limite_int,
            )
        )

    @action(detail=False, methods=["post"], url_path="entrada")
    def criar_entrada(self, request, slug=None):
        data = request.data.copy()
        data["laba_dbcr"] = "C"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="saida")
    def criar_saida(self, request, slug=None):
        data = request.data.copy()
        data["laba_dbcr"] = "D"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["put", "patch"], url_path="entrada")
    def atualizar_entrada(self, request, pk=None, slug=None):
        obj = self.get_object()
        if (obj.laba_dbcr or "").upper() != "C":
            return Response({"detail": "Lançamento não é do tipo entrada."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data["laba_dbcr"] = "C"
        serializer = self.get_serializer(obj, data=data, partial=(request.method.upper() == "PATCH"))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["put", "patch"], url_path="saida")
    def atualizar_saida(self, request, pk=None, slug=None):
        obj = self.get_object()
        if (obj.laba_dbcr or "").upper() != "D":
            return Response({"detail": "Lançamento não é do tipo saída."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data["laba_dbcr"] = "D"
        serializer = self.get_serializer(obj, data=data, partial=(request.method.upper() == "PATCH"))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path="entrada")
    def deletar_entrada(self, request, pk=None, slug=None):
        obj = self.get_object()
        if (obj.laba_dbcr or "").upper() != "C":
            return Response({"detail": "Lançamento não é do tipo entrada."}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="saida")
    def deletar_saida(self, request, pk=None, slug=None):
        obj = self.get_object()
        if (obj.laba_dbcr or "").upper() != "D":
            return Response({"detail": "Lançamento não é do tipo saída."}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
