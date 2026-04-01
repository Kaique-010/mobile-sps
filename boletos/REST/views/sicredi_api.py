from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.registry import get_licenca_db_config
from ...models import Carteira
from ...services.sicredi_api_service import SicrediCobrancaService, SicrediAPIError


class SicrediTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, carteira_codigo):
        db = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")
        filial = request.session.get("filial_id")

        if not empresa:
            return Response({"erro": "empresa_nao_identificada"}, status=status.HTTP_400_BAD_REQUEST)

        qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=748, cart_codi=carteira_codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        carteira = qs.first()
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)

        try:
            token = SicrediCobrancaService(carteira).get_access_token()
            return Response({"ok": True, "access_token": token}, status=status.HTTP_200_OK)
        except SicrediAPIError as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class SicrediBoletoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _load_carteira(self, request, carteira_codigo):
        db = get_licenca_db_config(request) or "default"
        empresa = request.session.get("empresa_id")
        filial = request.session.get("filial_id")
        qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=748, cart_codi=carteira_codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        return qs.first()

    def post(self, request, carteira_codigo):
        carteira = self._load_carteira(request, carteira_codigo)
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)

        try:
            payload = request.data.get("payload") or request.data
            retorno = SicrediCobrancaService(carteira).registrar_boleto(payload)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except SicrediAPIError as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, carteira_codigo):
        carteira = self._load_carteira(request, carteira_codigo)
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)

        nosso_numero = request.query_params.get("nosso_numero")
        if not nosso_numero:
            return Response({"erro": "nosso_numero_obrigatorio"}, status=status.HTTP_400_BAD_REQUEST)

        params = {
            "cooperativa": request.query_params.get("cooperativa"),
            "posto": request.query_params.get("posto"),
            "codigoBeneficiario": request.query_params.get("codigo_beneficiario"),
        }
        params = {k: v for k, v in params.items() if v not in (None, "")}

        try:
            retorno = SicrediCobrancaService(carteira).consultar_boleto(nosso_numero, params=params)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except SicrediAPIError as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, carteira_codigo):
        carteira = self._load_carteira(request, carteira_codigo)
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)

        nosso_numero = request.data.get("nosso_numero")
        acao = request.data.get("acao")
        payload = request.data.get("payload") or {}

        if not nosso_numero or not acao:
            return Response({"erro": "nosso_numero_e_acao_obrigatorios"}, status=status.HTTP_400_BAD_REQUEST)

        client = SicrediCobrancaService(carteira)
        try:
            if acao == "baixar":
                retorno = client.baixar_boleto(nosso_numero, payload=payload)
            else:
                retorno = client.alterar_boleto(nosso_numero, payload=payload)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except SicrediAPIError as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
