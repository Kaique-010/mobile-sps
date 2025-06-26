from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import date, timedelta
from django.db import IntegrityError, transaction
import logging

from core.middleware import get_licenca_slug
from .serializers import RecebimentoSdkSerializer
from .models import RecebimentoSdk, TituloReceberSdk

logger = logging.getLogger(__name__)


def gerar_titulos_para_recebimento(sdk_obj, slug):
    """
    Gera títulos a receber baseado no tipo de recebimento.
    Para PIX/débito: 1 título com status 'recebido'
    Para crédito: múltiplos títulos com status 'previsto'
    """
    try:
        if sdk_obj.sdk_tipo in ['pix', 'debito']:
            titulo = TituloReceberSdk.objects.using(slug).create(
                titu_empr=sdk_obj.sdk_empr,
                titu_fili=sdk_obj.sdk_fili,
                titu_rece=sdk_obj,
                titu_nume=1,
                titu_valo=sdk_obj.sdk_valo,
                titu_seri='SDK',
                titu_data=date.today(),
                titu_stat='recebido'
            )
            logger.info(f"Título criado para {sdk_obj.sdk_tipo}: {titulo.titu_id}")
            
        elif sdk_obj.sdk_tipo == 'credito':
            valor_parcela = sdk_obj.sdk_valo / sdk_obj.sdk_parc
            titulos_criados = []
            
            for i in range(1, sdk_obj.sdk_parc + 1):
                titulo = TituloReceberSdk.objects.using(slug).create(
                    titu_empr=sdk_obj.sdk_empr,
                    titu_fili=sdk_obj.sdk_fili,
                    titu_rece=sdk_obj,
                    titu_nume=i,
                    titu_valo=round(valor_parcela, 2),
                    titu_seri='SDK',
                    titu_data=date.today() + timedelta(days=30 * (i - 1)),
                    titu_stat='previsto'
                )
                titulos_criados.append(titulo.titu_id)
                
            logger.info(f"Títulos criados para crédito: {len(titulos_criados)} parcelas")
            
    except Exception as e:
        logger.error(f"Erro ao gerar títulos para recebimento {sdk_obj.sdk_id}: {str(e)}")
        raise  # Re-raise para ser capturado pela transação atômica


class RegistrarRecebimentoView(APIView):
    def post(self, request, slug=None):
        slug = get_licenca_slug()
        if not slug:
            return Response({"error": "Licença não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecebimentoSdkSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Usar transação atômica para garantir consistência
                with transaction.atomic(using=slug):
                    # Salvar o objeto usando a database correta
                    sdk_obj = RecebimentoSdk.objects.using(slug).create(**serializer.validated_data)
                    gerar_titulos_para_recebimento(sdk_obj, slug)
                    
                logger.info(f"Recebimento registrado com sucesso: {sdk_obj.sdk_pedi}")
                return Response({
                    'status': 'Recebimento registrado com sucesso',
                    'sdk_id': sdk_obj.sdk_id,
                    'sdk_pedi': sdk_obj.sdk_pedi
                }, status=status.HTTP_201_CREATED)
                
            except IntegrityError as e:
                logger.error(f"Erro de integridade ao registrar recebimento: {str(e)}")
                if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
                    return Response({
                        "non_field_errors": ["Já existe um recebimento registrado para esta combinação de empresa, filial e pedido."]
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        "error": "Erro de integridade no banco de dados."
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Erro inesperado ao registrar recebimento: {str(e)}")
                return Response({
                    "error": "Erro interno do servidor. Tente novamente."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
