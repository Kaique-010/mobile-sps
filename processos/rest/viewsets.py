from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.utils import get_db_from_slug
from processos.models import ChecklistItem, ChecklistModelo, Processo, ProcessoTipo
from processos.rest.serializers import (
    ChecklistItemSerializer,
    ChecklistModeloSerializer,
    ProcessoSerializer,
    ProcessoTipoSerializer,
)
from processos.services.checklist_service import ChecklistService
from processos.services.processo_service import ProcessoService
from processos.services.validacao_service import ValidacaoProcessoService


class BaseMultiDBViewSet(viewsets.ModelViewSet):
    def _ctx(self):
        slug = self.kwargs.get("slug")
        return {
            "db_alias": get_db_from_slug(slug) if slug else "default",
            "empresa": self.request.session.get("empresa_id") or self.request.headers.get("X-Empresa") or 1,
            "filial": self.request.session.get("filial_id") or self.request.headers.get("X-Filial") or 1,
            "usuario_id": self.request.session.get("usuario_id"),
        }


class ProcessoTipoViewSet(BaseMultiDBViewSet):
    serializer_class = ProcessoTipoSerializer

    def get_queryset(self):
        cfg = self._ctx()
        return ProcessoTipo.objects.using(cfg["db_alias"]).filter(prot_empr=cfg["empresa"], prot_fili=cfg["filial"])

    def create(self, request, *args, **kwargs):
        cfg = self._ctx()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tipo = ProcessoService.criar_tipo(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            nome=data["prot_nome"],
            codigo=data["prot_codi"],
            ativo=data.get("prot_ativ", True),
        )
        return Response(self.get_serializer(tipo).data, status=status.HTTP_201_CREATED)


class ChecklistModeloViewSet(BaseMultiDBViewSet):
    serializer_class = ChecklistModeloSerializer

    def get_queryset(self):
        cfg = self._ctx()
        return ChecklistModelo.objects.using(cfg["db_alias"]).filter(chmo_empr=cfg["empresa"], chmo_fili=cfg["filial"])

    def create(self, request, *args, **kwargs):
        cfg = self._ctx()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tipo = ProcessoTipo.objects.using(cfg["db_alias"]).get(id=data["chmo_proc_tipo_id"])
        modelo = ChecklistService.criar_modelo(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            processo_tipo=tipo,
            nome=data["chmo_nome"],
            versao=data.get("chmo_vers", 1),
            ativo=data.get("chmo_ativ", True),
        )
        return Response(self.get_serializer(modelo).data, status=status.HTTP_201_CREATED)


class ChecklistItemViewSet(BaseMultiDBViewSet):
    serializer_class = ChecklistItemSerializer

    def get_queryset(self):
        cfg = self._ctx()
        return ChecklistItem.objects.using(cfg["db_alias"]).filter(chit_empr=cfg["empresa"], chit_fili=cfg["filial"])

    def create(self, request, *args, **kwargs):
        cfg = self._ctx()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        modelo = ChecklistModelo.objects.using(cfg["db_alias"]).get(id=data["chit_mode_id"])
        item = ChecklistService.criar_item(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            modelo=modelo,
            descricao=data["chit_desc"],
            ordem=data.get("chit_orde", 0),
            obrigatorio=data.get("chit_obri", True),
        )
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)


class ProcessoViewSet(BaseMultiDBViewSet):
    serializer_class = ProcessoSerializer

    def get_queryset(self):
        cfg = self._ctx()
        return ProcessoService.listar(db_alias=cfg["db_alias"], empresa=cfg["empresa"], filial=cfg["filial"])

    def create(self, request, *args, **kwargs):
        cfg = self._ctx()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        processo = ProcessoService.criar(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            tipo_id=data["proc_tipo_id"],
            descricao=data["proc_desc"],
            usuario_id=cfg["usuario_id"],
        )
        return Response(self.get_serializer(processo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="salvar-checklist")
    def salvar_checklist(self, request, pk=None, slug=None):
        cfg = self._ctx()
        dados = request.data.get("respostas", {})
        ChecklistService.salvar_respostas(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            processo_id=pk,
            dados=dados,
        )
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="validar")
    def validar(self, request, pk=None, slug=None):
        cfg = self._ctx()
        resultado = ValidacaoProcessoService.validar_processo(
            db_alias=cfg["db_alias"],
            empresa=cfg["empresa"],
            filial=cfg["filial"],
            processo_id=pk,
            usuario_id=cfg["usuario_id"],
        )
        return Response(resultado)
