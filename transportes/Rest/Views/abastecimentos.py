from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Abastecusto
from transportes.serializers.abastecimento import AbastecimentoSerializer
from transportes.services.servico_de_abastecimento import AbastecimentoService


class AbastecimentoViewSet(viewsets.ViewSet):
    def _contexto(self, request, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")
        filial_id = request.session.get("filial_id") or 1
        usuario_id = request.session.get("usua_codi")
        return {
            "banco": banco,
            "empresa_id": int(empresa_id) if empresa_id else None,
            "filial_id": int(filial_id) if filial_id else None,
            "usuario_id": int(usuario_id) if usuario_id else None,
        }

    def _get_obj(self, request, abas_ctrl, slug=None):
        ctx = self._contexto(request, slug)
        return get_object_or_404(
            Abastecusto.objects.using(ctx["banco"]),
            abas_empr=ctx["empresa_id"],
            abas_fili=ctx["filial_id"],
            abas_ctrl=abas_ctrl,
        )

    def list(self, request, slug=None):
        ctx = self._contexto(request, slug)
        if not ctx["empresa_id"]:
            return Response({"results": []}, status=status.HTTP_200_OK)

        qs = Abastecusto.objects.using(ctx["banco"]).filter(abas_empr=ctx["empresa_id"])
        if ctx["filial_id"]:
            qs = qs.filter(abas_fili=ctx["filial_id"])
        qs = qs.order_by("-abas_data", "-abas_ctrl")

        serializer = AbastecimentoSerializer(qs, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, slug=None):
        obj = self._get_obj(request, pk, slug)
        return Response(AbastecimentoSerializer(obj).data, status=status.HTTP_200_OK)

    def create(self, request, slug=None):
        ctx = self._contexto(request, slug)
        serializer = AbastecimentoSerializer(data=request.data, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(AbastecimentoSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        obj = self._get_obj(request, pk, slug)
        serializer = AbastecimentoSerializer(instance=obj, data=request.data, partial=True, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(AbastecimentoSerializer(obj).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        obj = self._get_obj(request, pk, slug)
        AbastecimentoService.delete_abastecimento(
            abastecimento=obj,
            user_id=ctx.get("usuario_id"),
            using=ctx["banco"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

