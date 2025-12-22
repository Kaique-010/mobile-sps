from rest_framework.views import APIView
from core.dominio_handler import tratar_erro, tratar_sucesso
from core.excecoes import ErroDominio
from Licencas.utils import get_licenca_slug
from dashboards.utils import enviar_email

class EnviarEmail(APIView):
    def post(self, request, slug=None):
        try:
            slug = get_licenca_slug()

            if not slug:
                raise ErroDominio("Licença não encontrada.", codigo="licenca_nao_encontrada")
            
            email = request.data.get('email')
            dados = request.data.get('dados')
            
            if not email or not dados:
                raise ErroDominio('Email e dados são obrigatórios', codigo="dados_obrigatorios")
            
            enviado = enviar_email(email, dados)
            
            if enviado:
                return tratar_sucesso(mensagem='E-mail enviado com sucesso')
            
            raise ErroDominio('Falha ao enviar o e-mail.', codigo="falha_envio")

        except Exception as e:
            return tratar_erro(e)
