from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from core.excecoes import ErroDominio
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
import logging
import traceback

logger = logging.getLogger(__name__)

def tratar_erro(exc):
    """
    Trata exceções e retorna uma resposta padronizada de erro.
    """
    if isinstance(exc, ErroDominio):
        return Response(
            {
                "erro": exc.codigo,
                "mensagem": exc.mensagem,
                "detalhes": exc.detalhes,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if isinstance(exc, APIException):
        return Response(
            {
                "erro": exc.default_code,
                "mensagem": str(exc.detail),
                "detalhes": exc.get_full_details()
            },
            status=exc.status_code
        )
        
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {
                "erro": "recurso_nao_encontrado",
                "mensagem": "Recurso não encontrado.",
                "detalhes": str(exc)
            },
            status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, MultipleObjectsReturned):
        return Response(
            {
                "erro": "multiplos_registros",
                "mensagem": "Foram encontrados múltiplos registros para esta solicitação.",
                "detalhes": str(exc)
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Log o erro completo para debug
    logger.error(f"Erro interno não tratado: {exc}")
    logger.error(traceback.format_exc())

    return Response(
        {
            "erro": "erro_interno", 
            "mensagem": "Ocorreu um erro interno no servidor.",
            "detalhes": str(exc)
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

def tratar_sucesso(dados=None, mensagem=None, status_code=status.HTTP_200_OK):
    """
    Retorna uma resposta padronizada de sucesso.
    """
    response_data = {}

    if dados is not None:
        if isinstance(dados, dict):
            response_data = dados.copy()
        elif isinstance(dados, list):
            response_data['dados'] = dados
        else:
            response_data['dados'] = dados
    
    if mensagem:
        response_data['mensagem'] = mensagem
        
    return Response(response_data, status=status_code)
