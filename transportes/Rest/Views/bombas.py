from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.models import Bombas
from transportes.serializers.bombas import BombasSerializer


class BombasListApiView(APIView):
    def get(self, request, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")
        if not empresa_id:
            return Response({"results": []}, status=status.HTTP_200_OK)

        qs = Bombas.objects.using(banco).filter(bomb_empr=empresa_id).order_by("bomb_desc", "bomb_codi")
        return Response(
            {"results": BombasSerializer(qs, many=True).data},
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")

        serializer = BombasSerializer(
            data=request.data,
            context={"banco": banco, "empresa_id": empresa_id},
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            BombasSerializer(obj).data,
            status=status.HTTP_201_CREATED,
        )


class BombasDetailApiView(APIView):
    def get(self, request, bomb_codi: str, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")
        obj = get_object_or_404(
            Bombas.objects.using(banco),
            bomb_empr=empresa_id,
            bomb_codi=bomb_codi,
        )
        return Response(BombasSerializer(obj).data, status=status.HTTP_200_OK)

    def patch(self, request, bomb_codi: str, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")
        obj = get_object_or_404(
            Bombas.objects.using(banco),
            bomb_empr=empresa_id,
            bomb_codi=bomb_codi,
        )
        serializer = BombasSerializer(
            instance=obj,
            data=request.data,
            partial=True,
            context={"banco": banco, "empresa_id": empresa_id},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BombasSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, bomb_codi: str, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get("empresa_id")
        Bombas.objects.using(banco).filter(
            bomb_empr=empresa_id,
            bomb_codi=bomb_codi,
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

