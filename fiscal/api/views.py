from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import get_licenca_db_config
from fiscal.api.serializers import (
    GerarDevolucaoSerializer,
    GerarEntradaSerializer,
    ImportarXMLSerializer,
    NFeDocumentoSerializer,
    NFeDocumentoDetailSerializer,
    WizardFinalizarSerializer,
    WizardIniciarSerializer,
    WizardItensSerializer,
)
from fiscal.models import NFeDocumento
from fiscal.services.gerar_devolucao_service import GerarDevolucaoService
from fiscal.services.importar_xml_service import ImportarXMLService


class ImportarXMLView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ImportarXMLSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        service = ImportarXMLService(banco=banco)

        try:
            empresa = serializer.validated_data["empresa"]
            filial = serializer.validated_data["filial"]
            xml = (serializer.validated_data.get("xml") or "").strip()
            chave = (serializer.validated_data.get("chave") or "").strip()

            if xml:
                doc = service.importar(empresa=empresa, filial=filial, xml=xml)
            else:
                doc = service.importar_por_chave(empresa=empresa, filial=filial, chave=chave)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "id": doc.id,
                "empresa": doc.empresa,
                "filial": doc.filial,
                "chave": doc.chave,
                "tipo": doc.tipo,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"

        qs = NFeDocumento.objects.using(banco).all().order_by("-criado_em")
        empresa = request.query_params.get("empresa")
        filial = request.query_params.get("filial")
        tipo = request.query_params.get("tipo")
        if empresa is not None:
            qs = qs.filter(empresa=int(empresa))
        if filial is not None:
            qs = qs.filter(filial=int(filial))
        if tipo:
            tipo = str(tipo).strip().lower()
            if tipo in ("entrada", "saida"):
                qs = qs.filter(tipo=tipo)

        data = NFeDocumentoSerializer(qs[:200], many=True).data
        return Response(data)


class DocumentoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, documento_id: int, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"

        qs = NFeDocumento.objects.using(banco).filter(pk=int(documento_id))
        empresa = request.query_params.get("empresa")
        filial = request.query_params.get("filial")
        if empresa is not None:
            qs = qs.filter(empresa=int(empresa))
        if filial is not None:
            qs = qs.filter(filial=int(filial))

        doc = qs.first()
        if not doc:
            return Response({"detail": "Documento não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        return Response(NFeDocumentoDetailSerializer(doc).data)


class GerarDevolucaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GerarDevolucaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        service = GerarDevolucaoService(banco=banco)

        try:
            nota = service.gerar(
                documento_id=serializer.validated_data["documento_id"],
                empresa=serializer.validated_data["empresa"],
                filial=serializer.validated_data["filial"],
                emitir=serializer.validated_data.get("emitir") or False,
                usuario_id=getattr(getattr(request, "user", None), "id", None),
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "nota_id": nota.id,
                "empresa": nota.empresa,
                "filial": nota.filial,
                "finalidade": nota.finalidade,
                "tipo_operacao": nota.tipo_operacao,
            },
            status=status.HTTP_201_CREATED,
        )


class GerarEntradaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GerarEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        empresa = serializer.validated_data["empresa"]
        filial = serializer.validated_data["filial"]
        documento_id = serializer.validated_data["documento_id"]

        doc = (
            NFeDocumento.objects.using(banco)
            .filter(pk=int(documento_id), empresa=int(empresa), filial=int(filial))
            .first()
        )
        if not doc:
            return Response({"detail": "Documento não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        xml = (doc.xml_original or "").strip()
        if not xml:
            return Response({"detail": "Documento não possui XML."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from fiscal.services.entrada_xml_service import EntradaXMLService

            usuario_id = getattr(getattr(request, "user", None), "usua_codi", 0) or getattr(
                getattr(request, "user", None), "id", 0
            )
            service = EntradaXMLService(banco=banco)
            result = service.processar(
                empresa=int(empresa),
                filial=int(filial),
                documento_id=int(documento_id),
                usuario_id=int(usuario_id or 0),
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )


class WizardIniciarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = WizardIniciarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        service = EntradaWizardService(banco=banco)
        try:
            nota = service.iniciar(
                documento_id=serializer.validated_data["documento_id"],
                empresa=serializer.validated_data["empresa"],
                filial=serializer.validated_data["filial"],
                data_entrada=serializer.validated_data.get("data_entrada"),
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "nota_id": nota.pk,
                "empresa": nota.empresa,
                "filial": nota.filial,
                "numero_nota_fiscal": nota.numero_nota_fiscal,
                "serie": nota.serie,
                "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
                "data_entrada": nota.data_saida_entrada.isoformat() if nota.data_saida_entrada else None,
                "emitente": nota.emitente_razao_social,
                "valor_total": str(nota.valor_total_nota or ""),
            },
            status=status.HTTP_201_CREATED,
        )


class WizardPreprocessarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, nota_id: int, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        service = EntradaWizardService(banco=banco)
        try:
            data = service.itens_preprocessar(nota_id=int(nota_id))
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WizardFinanceiroView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, nota_id: int, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        service = EntradaWizardService(banco=banco)
        try:
            data = service.financeiro_preview(nota_id=int(nota_id))
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)

class WizardAutoMapearView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, nota_id: int, *args, **kwargs):
        serializer = WizardItensSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        service = EntradaWizardService(banco=banco)
        try:
            data = service.auto_mapear(nota_id=int(nota_id), itens=serializer.validated_data["itens"])
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WizardCriarProdutosView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, nota_id: int, *args, **kwargs):
        serializer = WizardItensSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        usuario_id = getattr(getattr(request, "user", None), "usua_codi", 0) or getattr(
            getattr(request, "user", None), "id", 0
        )
        service = EntradaWizardService(banco=banco)
        try:
            data = service.criar_produtos_faltantes(
                nota_id=int(nota_id),
                itens=serializer.validated_data["itens"],
                usuario_id=int(usuario_id or 0),
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data)


class WizardFinalizarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, nota_id: int, *args, **kwargs):
        serializer = WizardFinalizarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        banco = get_licenca_db_config(request) or "default"
        from fiscal.services.entrada_wizard_service import EntradaWizardService

        usuario_id = getattr(getattr(request, "user", None), "usua_codi", 0) or getattr(
            getattr(request, "user", None), "id", 0
        )
        service = EntradaWizardService(banco=banco)
        try:
            result = service.finalizar(
                nota_id=int(nota_id),
                entradas=serializer.validated_data["entradas"],
                usuario_id=int(usuario_id or 0),
                parcelas=serializer.validated_data.get("parcelas"),
                forma_pagamento=serializer.validated_data.get("forma_pagamento"),
            )
        except ValidationError as e:
            msg = str(e)
            if "título" in msg.lower() and "existe" in msg.lower():
                return Response({"detail": msg}, status=status.HTTP_409_CONFLICT)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(result, dict) and (result.get("status") == "titulo_existente"):
            return Response({"detail": "Título já existe para esta nota." , **result}, status=status.HTTP_409_CONFLICT)

        try:
            if isinstance(result, dict) and (result.get("status") == "sucesso"):
                pendentes = result.get("itens_pendentes") or []
                if isinstance(pendentes, list) and len(pendentes) == 0:
                    documento_id = serializer.validated_data.get("documento_id")
                    if documento_id:
                        from NotasDestinadas.models import NotaFiscalEntrada

                        nota = NotaFiscalEntrada.objects.using(banco).filter(pk=int(nota_id)).first()
                        if nota:
                            NFeDocumento.objects.using(banco).filter(
                                pk=int(documento_id),
                                empresa=int(nota.empresa),
                                filial=int(nota.filial),
                            ).delete()
        except Exception:
            pass
        return Response(result, status=status.HTTP_201_CREATED)


class WizardEntradasListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        banco = get_licenca_db_config(request) or "default"
        from NotasDestinadas.models import NotaFiscalEntrada

        empresa = request.query_params.get("empresa")
        filial = request.query_params.get("filial")

        qs = NotaFiscalEntrada.objects.using(banco).all()
        if empresa is not None:
            qs = qs.filter(empresa=int(empresa))
        if filial is not None:
            qs = qs.filter(filial=int(filial))
        qs = qs.order_by("-data_emissao", "-numero_nota_fiscal")[:200]

        data = []
        for n in qs:
            data.append(
                {
                    "id": n.pk,
                    "empresa": n.empresa,
                    "filial": n.filial,
                    "numero_nota_fiscal": n.numero_nota_fiscal,
                    "serie": n.serie,
                    "data_emissao": n.data_emissao.isoformat() if n.data_emissao else None,
                    "data_entrada": n.data_saida_entrada.isoformat() if n.data_saida_entrada else None,
                    "emitente": n.emitente_razao_social,
                    "valor_total_nota": str(n.valor_total_nota or ""),
                }
            )
        return Response(data)

