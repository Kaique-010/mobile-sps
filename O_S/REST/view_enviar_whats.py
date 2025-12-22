from rest_framework.views import APIView
from core.dominio_handler import tratar_erro, tratar_sucesso
from core.excecoes import ErroDominio
from Licencas.utils import get_licenca_slug
from .utils import enviar_whatsapp

class EnviarWhatsapp(APIView):
    def post(self, request, slug=None):
        try:
            slug = get_licenca_slug()

            if not slug:
                raise ErroDominio("Licença não encontrada.", codigo="licenca_nao_encontrada")
            
            cliente_id = request.data.get('cliente_id')
            dados = request.data.get('dados')
            
            if not cliente_id or not dados:
                raise ErroDominio('ID do Cliente e dados são obrigatórios', codigo="dados_obrigatorios")
            
            enviado, mensagem = enviar_whatsapp(cliente_id, dados)
            
            if enviado:
                return tratar_sucesso(mensagem=mensagem)
            
            raise ErroDominio(mensagem, codigo="erro_whatsapp")
            
        except Exception as e:
            return tratar_erro(e)
