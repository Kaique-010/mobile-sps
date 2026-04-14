from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Entidades.models import Entidades
from core.utils import get_db_from_slug, get_licenca_db_config
from transportes.serializers.transp_moto import TranspMotoSerializer
from transportes.services.transp_moto_sync_service import TranspMotoSyncService


class TranspMotoListApiView(APIView):
    def get(self, request, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get('empresa_id')
        qs = Entidades.objects.using(banco).filter(enti_empr=empresa_id, enti_tien__in=['T', 'M']).order_by('enti_clie')
        return Response({'results': TranspMotoSerializer(qs, many=True).data}, status=status.HTTP_200_OK)


class TranspMotoUpdateApiView(APIView):
    def patch(self, request, enti_clie, slug=None):
        banco = get_db_from_slug(slug) if slug else get_licenca_db_config(request)
        empresa_id = request.session.get('empresa_id')
        filial_id = request.session.get('filial_id') or 1

        obj = get_object_or_404(
            Entidades.objects.using(banco),
            enti_empr=empresa_id,
            enti_clie=enti_clie,
            enti_tien__in=['T', 'M'],
        )
        serializer = TranspMotoSerializer(instance=obj, data=request.data, partial=True, context={'using': banco})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if obj.enti_tien == 'M':
            TranspMotoSyncService.sync_entidade_para_motorista(
                banco=banco,
                empresa_id=empresa_id,
                filial_id=filial_id,
                entidade_id=obj.enti_clie,
            )
        return Response(TranspMotoSerializer(obj).data, status=status.HTTP_200_OK)
