from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import BombasSaldos
from transportes.serializers.bombas_saldos import BombasSaldosSerializer
from transportes.services.bombas_saldos import BombasSaldosService


class BombasSaldosViewSet(viewsets.ViewSet):
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

    def _get_obj(self, request, bomb_id, slug=None):
        ctx = self._contexto(request, slug)
        return get_object_or_404(
            BombasSaldos.objects.using(ctx["banco"]),
            bomb_id=bomb_id,
            bomb_empr=ctx["empresa_id"],
            bomb_fili=ctx["filial_id"],
        )

    def list(self, request, slug=None):
        ctx = self._contexto(request, slug)
        if not ctx["empresa_id"]:
            return Response({"results": []}, status=status.HTTP_200_OK)

        qs = BombasSaldos.objects.using(ctx["banco"]).filter(
            bomb_empr=ctx["empresa_id"],
            bomb_fili=ctx["filial_id"],
        ).order_by("-bomb_data", "-bomb_id")

        return Response({"results": BombasSaldosSerializer(qs, many=True).data}, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, slug=None):
        obj = self._get_obj(request, pk, slug)
        return Response(BombasSaldosSerializer(obj).data, status=status.HTTP_200_OK)

    def create(self, request, slug=None):
        ctx = self._contexto(request, slug)
        serializer = BombasSaldosSerializer(data=request.data, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(BombasSaldosSerializer(obj).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        obj = self._get_obj(request, pk, slug)
        serializer = BombasSaldosSerializer(instance=obj, data=request.data, partial=True, context=ctx)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(BombasSaldosSerializer(obj).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None, slug=None):
        ctx = self._contexto(request, slug)
        BombasSaldosService.excluir_movimentacao(
            using=ctx["banco"],
            empresa_id=int(ctx["empresa_id"]),
            filial_id=int(ctx["filial_id"]),
            bomb_id=int(pk),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

