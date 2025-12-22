from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from ..dominio.excecoes import ErroDominio
import logging
import traceback

logger = logging.getLogger(__name__)

def tratar_erro(exc):
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
        return Response(exc.detail, status=exc.status_code)

    # Log o erro completo para debug
    logger.error(f"Erro interno não tratado: {exc}")
    logger.error(traceback.format_exc())

    return Response(
        {
            "erro": "erro_interno", 
            "mensagem": str(exc) # Retornar a mensagem ajuda no debug imediato
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
