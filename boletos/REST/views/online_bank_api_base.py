from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.utils import get_db_from_slug
from ...models import Carteira
from ...services.boleto_online_factory import get_online_boleto_service


class BaseOnlineBankAPIView(APIView):
    permission_classes = [IsAuthenticated]
    bank_code = None

    def _db(self, request):
        slug = self.kwargs.get('slug') or request.session.get('slug')
        try:
            return get_db_from_slug(slug) if slug else 'default'
        except Exception:
            return 'default'

    def _load_carteira(self, request, carteira_codigo):
        db = self._db(request)
        empresa = request.session.get("empresa_id")
        filial = request.session.get("filial_id")
        qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=int(self.bank_code), cart_codi=carteira_codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        return qs.first()

    def _service(self, carteira):
        return get_online_boleto_service(self.bank_code, carteira)

    def post(self, request, carteira_codigo):
        carteira = self._load_carteira(request, carteira_codigo)
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)
        payload = request.data.get("payload") or request.data
        service, service_error = self._service(carteira)
        try:
            retorno = service.registrar_boleto(payload)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except service_error as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, carteira_codigo):
        carteira = self._load_carteira(request, carteira_codigo)
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)
        nosso_numero = request.query_params.get("nosso_numero")
        if not nosso_numero:
            return Response({"erro": "nosso_numero_obrigatorio"}, status=status.HTTP_400_BAD_REQUEST)
        service, service_error = self._service(carteira)
        try:
            retorno = service.consultar_boleto(nosso_numero)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except service_error as exc:
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

        service, service_error = self._service(carteira)
        try:
            if acao == "baixar":
                retorno = service.baixar_boleto(nosso_numero, payload=payload)
            elif acao == "cancelar":
                retorno = service.cancelar_boleto(nosso_numero, payload=payload)
            elif acao in ("alterar", "alterar_vencimento"):
                retorno = service.alterar_boleto(nosso_numero, payload=payload)
            else:
                return Response({"erro": "acao_invalida"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"ok": True, "retorno": retorno}, status=status.HTTP_200_OK)
        except service_error as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class BaseOnlineBankTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]
    bank_code = None

    def _db(self, request):
        slug = self.kwargs.get('slug') or request.session.get('slug')
        try:
            return get_db_from_slug(slug) if slug else 'default'
        except Exception:
            return 'default'

    def post(self, request, carteira_codigo):
        db = self._db(request)
        empresa = request.session.get("empresa_id")
        filial = request.session.get("filial_id")
        qs = Carteira.objects.using(db).filter(cart_empr=empresa, cart_banc=int(self.bank_code), cart_codi=carteira_codigo)
        if filial:
            qs = qs.filter(cart_fili=filial)
        carteira = qs.first()
        if not carteira:
            return Response({"erro": "carteira_nao_encontrada"}, status=status.HTTP_404_NOT_FOUND)

        service, service_error = get_online_boleto_service(self.bank_code, carteira)
        try:
            token_method = getattr(service, 'get_access_token', None) or getattr(service, '_token')
            token = token_method()
            return Response({"ok": True, "access_token": token}, status=status.HTTP_200_OK)
        except service_error as exc:
            return Response({"ok": False, "erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
