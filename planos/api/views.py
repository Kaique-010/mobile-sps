from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from planos.service import PlanoService
import logging

logger = logging.getLogger(__name__)

class TrialSignupView(APIView):
    """
    Endpoint para criar um novo ambiente de teste (Trial).
    Recebe:
    {
        "nome_empresa": "Minha Empresa",
        "cnpj": "00000000000000",
        "email": "admin@empresa.com",
        "nome_fantasia": "Minha Empresa Fantasia", # Opcional
        "telefone": "11999999999", # Opcional
        "endereco": "Rua X", # Opcional
        "cidade": "Cidade", # Opcional
        "uf": "SP", # Opcional
        "nome_filial": "Matriz" # Opcional
    }
    """
    permission_classes = [] # Aberto para cadastro
    authentication_classes = []

    def post(self, request):
        try:
            dados = request.data
            nome = dados.get('nome_empresa')
            cnpj = dados.get('cnpj')
            
            if not nome or not cnpj:
                return Response(
                    {"error": "Campos obrigatórios: nome_empresa, cnpj"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            modulos = dados.get('modulos', [])
            
            logger.info(f"Iniciando criação de trial para {nome} ({cnpj})")
            
            # Chama o serviço
            result = PlanoService.criar_ambiente_trial(dados, modulos_liberados=modulos)
            
            return Response({
                "message": "Ambiente criado com sucesso!",
                "slug": result['licenca'].slug,
                "db_name": result['licenca'].db_name,
                "plano": result['plano'].plan_nome,
                "usuario": result['usuario'].usua_nome,
                "senha_inicial": "123mudar"
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Erro no signup trial: {e}", exc_info=True)
            return Response({"error": "Erro interno ao processar solicitação."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
