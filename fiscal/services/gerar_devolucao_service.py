from decimal import Decimal, InvalidOperation

from typing import Dict, List

from django.core.exceptions import ValidationError
from django.db import transaction

from Entidades.models import Entidades
from Entidades.utils import proxima_entidade
from Licencas.models import Filiais
from Notas_Fiscais.services.nota_service import NotaService
from Produtos.models import Produtos
from fiscal.repositories.nfe_repository import NFeRepository
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader


class GerarDevolucaoService:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"
        self.repo = NFeRepository(banco=self.banco)

    def gerar(self, *, documento_id: int, empresa: int, filial: int, emitir: bool = False):
        doc = self.repo.get_documento(documento_id)
        doc_json = doc.json_dict or {}

        if not doc_json:
            raise ValidationError("Documento não possui JSON normalizado.")

        tipo_doc = (doc_json.get("tipo") or doc.tipo or "").strip().lower()
        if tipo_doc not in ("entrada", "saida"):
            tipo_doc = "entrada"

        destinatario_info, tipo_operacao = self._resolver_destinatario_e_tipo_operacao(tipo_doc, doc_json)
        destinatario = self._get_or_create_entidade(empresa=empresa, participante=destinatario_info)

        itens_payload = self._montar_itens(empresa=empresa, itens=doc_json.get("itens") or [])

        nota_data = {
            "modelo": "55",
            "tipo_operacao": tipo_operacao,
            "finalidade": 4,
            "destinatario": int(destinatario.enti_clie),
        }

        with transaction.atomic(using=self.banco):
            nota = NotaService.criar(
                data=nota_data,
                itens=itens_payload,
                impostos_map=None,
                transporte=None,
                empresa=int(empresa),
                filial=int(filial),
                database=self.banco,
            )

        if emitir:
            self._validar_certificado(empresa=empresa, filial=filial)

        return nota

    def _resolver_destinatario_e_tipo_operacao(self, tipo_doc: str, doc_json: dict):
        if tipo_doc == "entrada":
            return doc_json.get("emitente") or {}, 1
        return doc_json.get("destinatario") or {}, 0

    def _montar_itens(self, *, empresa: int, itens: List[Dict]):
        faltantes = []
        payload = []

        for item in itens:
            cprod = str(item.get("cProd") or "").strip()
            cean = str(item.get("cEAN") or "").strip()
            xprod = str(item.get("xProd") or "").strip()

            produto = self._resolver_produto(empresa=empresa, cprod=cprod, cean=cean, xprod=xprod)
            if not produto:
                faltantes.append({"cProd": cprod, "cEAN": cean, "xProd": xprod})
                continue

            quantidade = _to_decimal(item.get("qCom")) or Decimal("0")
            unitario = _to_decimal(item.get("vUnCom")) or Decimal("0")
            desconto = _to_decimal(item.get("vDesc")) or Decimal("0")

            payload.append(
                {
                    "produto": str(getattr(produto, "prod_codi", "") or ""),
                    "quantidade": float(quantidade),
                    "unitario": float(unitario),
                    "desconto": float(desconto),
                    "ncm": str(item.get("NCM") or "").strip(),
                    "cest": str(item.get("CEST") or "").strip() or None,
                    "cfop": "",
                }
            )

        if faltantes:
            exemplos = ", ".join(f"{i.get('cProd') or '?'}({i.get('xProd') or '?'})" for i in faltantes[:5])
            raise ValidationError(
                f"Não foi possível mapear {len(faltantes)} itens para Produtos. Exemplos: {exemplos}"
            )

        return payload

    def _resolver_produto(self, *, empresa: int, cprod: str, cean: str, xprod: str):
        qs = Produtos.objects.using(self.banco).filter(prod_empr=str(empresa))

        if cprod:
            p = qs.filter(prod_codi=cprod).first()
            if p:
                return p

        cean_digits = "".join(ch for ch in cean if ch.isdigit())
        if cean_digits and cean_digits not in ("0", "SEMGTIN", "SEM GTIN"):
            p = qs.filter(prod_gtin=cean_digits).first()
            if p:
                return p

        nome = (xprod or "").strip()
        if nome and len(nome) >= 6:
            p = qs.filter(prod_nome__iexact=nome).first()
            if p:
                return p

        return None

    def _get_or_create_entidade(self, *, empresa: int, participante: dict):
        doc = "".join(ch for ch in str(participante.get("documento") or "") if ch.isdigit())
        if not doc:
            raise ValidationError("Documento do destinatário não encontrado no XML.")

        qs = Entidades.objects.using(self.banco).filter(enti_empr=int(empresa))
        if len(doc) == 14:
            entidade = qs.filter(enti_cnpj=doc).first()
        else:
            entidade = qs.filter(enti_cpf=doc).first()

        if entidade:
            return entidade

        ender = participante.get("ender") or {}

        novo_id = proxima_entidade(int(empresa), 0, self.banco)

        data = {
            "enti_empr": int(empresa),
            "enti_clie": int(novo_id),
            "enti_nome": (participante.get("nome") or "").strip() or doc,
            "enti_fant": (participante.get("fantasia") or "").strip() or (participante.get("nome") or "").strip() or doc,
            "enti_tipo_enti": "FO",
            "enti_cpf": doc if len(doc) == 11 else "",
            "enti_cnpj": doc if len(doc) == 14 else "",
            "enti_insc_esta": (participante.get("ie") or "").strip(),
            "enti_cep": "".join(ch for ch in str(ender.get("CEP") or "") if ch.isdigit())[:8] or "00000000",
            "enti_ende": (ender.get("xLgr") or "").strip() or "SEM ENDEREÇO",
            "enti_nume": (ender.get("nro") or "").strip() or "S/N",
            "enti_bair": (ender.get("xBairro") or "").strip() or "CENTRO",
            "enti_cida": (ender.get("xMun") or "").strip() or "NÃO INFORMADO",
            "enti_esta": (ender.get("UF") or "").strip().upper() or "SP",
            "enti_fone": "".join(ch for ch in str(ender.get("fone") or "") if ch.isdigit())[:14] or "",
            "enti_celu": "",
            "enti_emai": "",
        }

        return Entidades.objects.using(self.banco).create(**data)

    def _validar_certificado(self, *, empresa: int, filial: int):
        filial_obj = (
            Filiais.objects.using(self.banco)
            .defer("empr_cert_digi")
            .filter(empr_empr=int(empresa), empr_codi=int(filial))
            .first()
        )
        if not filial_obj:
            raise ValidationError("Filial não encontrada para validar certificado.")

        cert_path, cert_pass = CertificadoLoader(filial_obj).load()
        if not cert_path:
            raise ValidationError("Certificado não encontrado para a filial.")
        if cert_pass is None:
            raise ValidationError("Senha do certificado não encontrada para a filial.")


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None
