from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Custos
from transportes.serializers.lancamento_custos import LancamentoCustosSerializer
from transportes.services.servico_de_lancamento_custos import LancamentoCustosService


class LancamentoCustosViewSet(viewsets.ViewSet):
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

    def _get_obj(self, request, lacu_ctrl, slug=None):
        ctx = self._contexto(request, slug)
        return get_object_or_404(
            Custos.objects.using(ctx["banco"]),
            lacu_empr=ctx["empresa_id"],
            lacu_fili=ctx["filial_id"],
            lacu_ctrl=lacu_ctrl,
        )

    def list(self, request, slug=None):
        ctx = self._contexto(request, slug)
        if not ctx["empresa_id"]:
            return Response({"results": []}, status=status.HTTP_200_OK)

        qs = Custos.objects.using(ctx["banco"]).filter(lacu_empr=ctx["empresa_id"])
        if ctx["filial_id"]:
            qs = qs.filter(lacu_fili=ctx["filial_id"])
        qs = qs.order_by("-lacu_data", "-lacu_ctrl")

        serializer = LancamentoCustosSerializer(qs, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, slug=None):
        obj = self._get_obj(request, pk, slug)
        return Response(LancamentoCustosSerializer(obj).data, status=status.HTTP_200_OK)

    def create(self, request, slug=None):
        ctx = self._contexto(request, slug)
        serializer = LancamentoCustosSerializer(data=request.data, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(LancamentoCustosSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        obj = self._get_obj(request, pk, slug)
        serializer = LancamentoCustosSerializer(instance=obj, data=request.data, partial=True, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(LancamentoCustosSerializer(obj).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        obj = self._get_obj(request, pk, slug)
        LancamentoCustosService.delete_custo(
            custo=obj,
            user_id=ctx.get("usuario_id"),
            using=ctx["banco"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
