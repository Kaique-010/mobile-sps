from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import date, timedelta

from core.middleware import get_licenca_slug
from .serializers import RecebimentoSdkSerializer
from .models import RecebimentoSdk, TituloReceberSdk


def gerar_titulos_para_recebimento(sdk_obj, slug):
    if sdk_obj.sdk_tipo in ['pix', 'debito']:
        TituloReceberSdk.objects.using(slug).create(
            titu_empr=sdk_obj.sdk_empr,
            titu_fili=sdk_obj.sdk_fili,
            titu_rece=sdk_obj,
            titu_nume=1,
            titu_valo=sdk_obj.sdk_valo,
            titu_seri='SDK',
            titu_data=date.today(),
            titu_stat='recebido'
        )
    elif sdk_obj.sdk_tipo == 'credito':
        valor_parcela = sdk_obj.sdk_valo / sdk_obj.sdk_parc
        for i in range(1, sdk_obj.sdk_parc + 1):
            TituloReceberSdk.objects.using(slug).create(
                titu_empr=sdk_obj.sdk_empr,
                titu_fili=sdk_obj.sdk_fili,
                titu_rece=sdk_obj,
                titu_nume=i,
                titu_valo=round(valor_parcela, 2),
                titu_seri='SDK',
                titu_data=date.today() + timedelta(days=30 * (i - 1)),
                titu_stat='previsto'
            )


class RegistrarRecebimentoView(APIView):
    def post(self, request, slug=None):
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecebimentoSdkSerializer(data=request.data)
        if serializer.is_valid():
            sdk_obj = serializer.save(using=slug)
            gerar_titulos_para_recebimento(sdk_obj, slug)
            return Response({'status': 'Recebimento registrado com sucesso'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
