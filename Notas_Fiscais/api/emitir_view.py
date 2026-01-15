from django.http import JsonResponse, HttpResponse
from ..aplicacao.emissao_service import EmissaoService
from core.utils import get_db_from_slug
from core.dominio_handler import tratar_erro
from rest_framework.response import Response as DRFResponse
from ..models import Nota
from ..utils.sefaz_messages import get_sefaz_message

try:
    from brazilfiscalreport.danfe import Danfe
except ImportError:
    Danfe = None


def emitir_nota(request, slug, nota_id):
    try:
        db = get_db_from_slug(slug)
        service = EmissaoService(slug, db)
        resposta = service.emitir(nota_id)
        
        # Enriquece a resposta com mensagem amigável
        status = resposta.get("status")
        motivo_original = resposta.get("motivo")
        mensagem_amigavel = get_sefaz_message(status, motivo_original)
        
        # Se status for None ou 0, talvez não seja erro da SEFAZ, mas interno
        if status:
            resposta["mensagem"] = mensagem_amigavel
            # Se não for autorizado (100) nem processamento (103, 105), pode ser erro
            if status != 100:
                resposta["erro"] = mensagem_amigavel

        return JsonResponse(resposta)
    except Exception as e:
        drf_response = tratar_erro(e)
        if isinstance(drf_response, DRFResponse):
            data = drf_response.data
            status_code = drf_response.status_code
            if isinstance(data, dict):
                msg = (
                    data.get("mensagem")
                    or data.get("detalhes")
                    or data.get("erro")
                    or str(e)
                )
                data["mensagem"] = msg
        else:
            data = {"erro": "erro_interno", "mensagem": str(e)}
            status_code = 500
        return JsonResponse(data, status=status_code)


def imprimir_danfe(request, slug, nota_id):
    try:
        if Danfe is None:
             return JsonResponse({"erro": "Biblioteca de impressão não instalada (BrazilFiscalReport)"}, status=500)

        db = get_db_from_slug(slug)
        nota = Nota.objects.using(db).get(id=nota_id)

        xml_content = nota.xml_autorizado or nota.xml_assinado
        
        if not xml_content:
             return JsonResponse({"erro": "Nota não possui XML gerado para impressão."}, status=400)

        if isinstance(xml_content, (bytes, bytearray)):
            xml_content = xml_content.decode("utf-8", errors="ignore")

        danfe = Danfe(xml_content)
        pdf_str = danfe.output(dest="S")
        if isinstance(pdf_str, (bytes, bytearray)):
            pdf_bytes = bytes(pdf_str)
        else:
            pdf_bytes = pdf_str.encode("latin-1")
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="NFe_{nota.numero}.pdf"'
        return response

    except Exception as e:
        # Tratamento de erro simplificado para o endpoint de impressão
        return JsonResponse({"erro": "Falha ao gerar PDF", "detalhes": str(e)}, status=500)
