from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date

import logging
from typing import Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from Entidades.models import Entidades
from Entidades.utils import proxima_entidade
from Entradas_Estoque.models import EntradaEstoque
from Licencas.models import Filiais
from Notas_Fiscais.services.nota_service import NotaService
from Produtos.models import SaldoProduto
from Saidas_Estoque.models import SaidasEstoque
from fiscal.engines.devolucao_engine import DevolucaoEngine
from fiscal.normalizers.nfe_normalizer import dumps_json, normalize_nfe_dict
from fiscal.parser.nfe_xml_parser import parse_nfe
from Produtos.models import Produtos
from fiscal.repositories.nfe_repository import NFeRepository
from Notas_Fiscais.infrastructure.certificado_loader import CertificadoLoader


logger = logging.getLogger(__name__)


class GerarDevolucaoService:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"
        self.repo = NFeRepository(banco=self.banco)
        self.devolucao_engine = DevolucaoEngine()

    def gerar(self, *, documento_id: int, empresa: int, filial: int, emitir: bool = False, usuario_id: Optional[int] = None):
        logger.debug(
            "[devolucao] iniciar gerar: banco=%s documento_id=%s empresa=%s filial=%s emitir=%s",
            self.banco,
            documento_id,
            empresa,
            filial,
            emitir,
        )
        doc = self.repo.get_documento(documento_id)
        doc_json = doc.json_dict or {}
        if self._json_parece_corrompido(doc_json) and (doc.xml_original or "").strip():
            try:
                reprocessado = normalize_nfe_dict(parse_nfe(doc.xml_original or ""))
                if reprocessado and not self._json_parece_corrompido(reprocessado):
                    doc_json = reprocessado
                    doc.json_normalizado = dumps_json(reprocessado)
                    doc.tipo = (reprocessado.get("tipo") or doc.tipo or "").strip().lower() or doc.tipo
                    doc.chave = (reprocessado.get("chave") or doc.chave or "").strip() or doc.chave
                    doc.save(using=self.banco, update_fields=["json_normalizado", "tipo", "chave"])
                    logger.debug(
                        "[devolucao] json reprocessado do xml_original e persistido: documento_id=%s chave=%s",
                        documento_id,
                        doc.chave,
                    )
            except Exception:
                logger.exception(
                    "[devolucao] falha ao reprocessar xml_original: documento_id=%s",
                    documento_id,
                )
        doc_json = self.devolucao_engine.processar_devolucao(doc_json)
        
        if not doc_json:
            raise ValidationError("Documento não possui JSON normalizado.")

        tipo_doc = (doc_json.get("tipo") or doc.tipo or "").strip().lower()
        if tipo_doc not in ("entrada", "saida"):
            tipo_doc = "entrada"

        logger.debug(
            "[devolucao] documento normalizado: chave=%s tipo=%s itens=%s",
            str(doc_json.get("chave") or "").strip(),
            tipo_doc,
            len(doc_json.get("itens") or []),
        )

        destinatario_info, tipo_operacao = self._resolver_destinatario_e_tipo_operacao(tipo_doc, doc_json)
        destinatario = self._get_or_create_entidade(empresa=empresa, participante=destinatario_info)

        itens_payload = self._montar_itens(empresa=empresa, itens=doc_json.get("itens") or [])
        if int(tipo_operacao) == 1:
            self._validar_estoque_para_saida(
                empresa=int(empresa),
                filial=int(filial),
                itens_payload=itens_payload,
            )

        nota_data = {
            "modelo": "55",
            "tipo_operacao": tipo_operacao,
            "finalidade": 4,
            "destinatario": int(destinatario.enti_clie),
            "chave_referenciada": str(doc_json.get("chave") or "").strip() or None,
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
            self._gerar_movimentacao_estoque(
                nota=nota,
                empresa=int(empresa),
                filial=int(filial),
                tipo_operacao=int(tipo_operacao),
                entidade_id=int(destinatario.enti_clie),
                itens_payload=itens_payload,
                usuario_id=int(usuario_id) if usuario_id else 1,
            )

        if emitir:
            self._validar_certificado(empresa=empresa, filial=filial)

        return nota

    def _json_parece_corrompido(self, doc_json: dict) -> bool:
        if not isinstance(doc_json, dict) or not doc_json:
            return True
        chave = str(doc_json.get("chave") or "").strip()
        if len(chave) != 44:
            return True
        itens = doc_json.get("itens") or []
        if not isinstance(itens, list):
            return True
        for item in itens:
            if not isinstance(item, dict):
                return True
            cfop = str(item.get("CFOP") or "").strip()
            ncm = str(item.get("NCM") or "").strip()
            if cfop and len(cfop) < 4:
                return True
            if ncm and len(ncm) < 8:
                return True
        return False

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
                logger.debug(
                    "[devolucao] produto nao mapeado: empresa=%s cProd=%s cEAN=%s xProd=%s NCM=%s CFOP=%s",
                    empresa,
                    cprod,
                    cean,
                    xprod,
                    str(item.get("NCM") or "").strip(),
                    str(item.get("CFOP") or "").strip(),
                )
                faltantes.append({"cProd": cprod, "cEAN": cean, "xProd": xprod})
                continue

            quantidade = _to_decimal(item.get("qCom")) or Decimal("0")
            unitario = _to_decimal(item.get("vUnCom")) or Decimal("0")
            desconto = _to_decimal(item.get("vDesc")) or Decimal("0")

            cfop = str(item.get("cfop_devolucao") or "").strip()
            if not cfop:
                logger.debug(
                    "[devolucao] item sem cfop_devolucao: empresa=%s produto=%s cProd=%s xProd=%s CFOP_xml=%s",
                    empresa,
                    str(getattr(produto, "prod_codi", "") or ""),
                    cprod,
                    xprod,
                    str(item.get("CFOP") or "").strip(),
                )
            payload.append(
                {
                    "produto": str(getattr(produto, "prod_codi", "") or ""),
                    "quantidade": float(quantidade),
                    "unitario": float(unitario),
                    "desconto": float(desconto),
                    "ncm": str(item.get("NCM") or "").strip(),
                    "cest": str(item.get("CEST") or "").strip() or None,
                    "cfop": cfop,
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
                logger.debug("[devolucao] produto mapeado por cProd: empresa=%s cProd=%s", empresa, cprod)
                return p

        cean_digits = "".join(ch for ch in cean if ch.isdigit())
        if cean_digits and cean_digits not in ("0", "SEMGTIN", "SEM GTIN"):
            p = qs.filter(prod_gtin=cean_digits).first()
            if p:
                logger.debug(
                    "[devolucao] produto mapeado por GTIN: empresa=%s cEAN=%s gtin=%s",
                    empresa,
                    cean,
                    cean_digits,
                )
                return p

        nome = (xprod or "").strip()
        if nome and len(nome) >= 6:
            p = qs.filter(prod_nome__iexact=nome).first()
            if p:
                logger.debug(
                    "[devolucao] produto mapeado por nome: empresa=%s xProd=%s",
                    empresa,
                    nome,
                )
                return p

        logger.debug(
            "[devolucao] produto nao encontrado: empresa=%s cProd=%s cEAN=%s xProd=%s",
            empresa,
            cprod,
            cean,
            (xprod or "").strip(),
        )
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

    def _to_money(self, valor: Decimal) -> Decimal:
        try:
            return (valor or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")

    def _to_qty(self, valor: Decimal) -> Decimal:
        try:
            return (valor or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")

    def _obter_saldo_produto(self, *, empresa: int, filial: int, produto: str) -> Decimal:
        sp = (
            SaldoProduto.objects.using(self.banco)
            .filter(produto_codigo=produto, empresa=str(empresa), filial=str(filial))
            .first()
        )
        if sp is not None:
            try:
                return Decimal(str(getattr(sp, "saldo_estoque", 0) or 0))
            except Exception:
                return Decimal("0")

        total_entradas = (
            EntradaEstoque.objects.using(self.banco)
            .filter(entr_empr=int(empresa), entr_fili=int(filial), entr_prod=str(produto))
            .aggregate(total=Sum("entr_quan"))
            .get("total")
            or 0
        )
        total_saidas = (
            SaidasEstoque.objects.using(self.banco)
            .filter(said_empr=int(empresa), said_fili=int(filial), said_prod=str(produto))
            .aggregate(total=Sum("said_quan"))
            .get("total")
            or 0
        )
        return Decimal(str(total_entradas or 0)) - Decimal(str(total_saidas or 0))

    def _validar_estoque_para_saida(self, *, empresa: int, filial: int, itens_payload: List[Dict]):
        if not itens_payload:
            raise ValidationError("Nenhum item encontrado para gerar a devolução.")

        req_por_produto: Dict[str, Decimal] = {}
        for item in itens_payload:
            prod = str(item.get("produto") or "").strip()
            qtd = Decimal(str(item.get("quantidade") or 0))
            if not prod or qtd <= 0:
                continue
            req_por_produto[prod] = req_por_produto.get(prod, Decimal("0")) + qtd

        if not req_por_produto:
            raise ValidationError("Nenhum item com quantidade válida para gerar a devolução.")

        nomes_map = {}
        try:
            codigos = list(req_por_produto.keys())
            qs = Produtos.objects.using(self.banco).filter(prod_empr=str(empresa), prod_codi__in=codigos)
            nomes_map = {str(p.prod_codi): str(p.prod_nome or "").strip() for p in qs}
        except Exception:
            nomes_map = {}

        for prod, req in req_por_produto.items():
            saldo = self._obter_saldo_produto(empresa=empresa, filial=filial, produto=prod)
            if saldo < req:
                nome = nomes_map.get(prod) or prod
                raise ValidationError(f"Estoque insuficiente para {nome}. Saldo: {saldo} / Necessário: {req}.")

    def _gerar_movimentacao_estoque(
        self,
        *,
        nota,
        empresa: int,
        filial: int,
        tipo_operacao: int,
        entidade_id: int,
        itens_payload: List[Dict],
        usuario_id: int,
    ):
        mov_data = getattr(nota, "data_emissao", None) or timezone.now().date()
        if not isinstance(mov_data, date):
            mov_data = timezone.now().date()

        if int(tipo_operacao) == 1:
            seq = int(SaidasEstoque.objects.using(self.banco).aggregate(max_sequ=Max("said_sequ")).get("max_sequ") or 0)
            for item in itens_payload:
                prod = str(item.get("produto") or "").strip()
                if not prod:
                    continue
                qtd = self._to_qty(Decimal(str(item.get("quantidade") or 0)))
                if qtd <= 0:
                    continue
                unit = Decimal(str(item.get("unitario") or 0))
                desc = Decimal(str(item.get("desconto") or 0))
                total = self._to_money((qtd * unit) - desc)
                existente = (
                    SaidasEstoque.objects.using(self.banco)
                    .filter(said_empr=int(empresa), said_fili=int(filial), said_prod=prod, said_data=mov_data)
                    .first()
                )
                if existente:
                    existente.said_quan = self._to_qty(Decimal(str(existente.said_quan or 0)) + qtd)
                    existente.said_tota = self._to_money(Decimal(str(existente.said_tota or 0)) + total)
                    if not getattr(existente, "said_enti", None):
                        existente.said_enti = str(entidade_id)
                    if not getattr(existente, "said_usua", None):
                        existente.said_usua = int(usuario_id)
                    if not getattr(existente, "said_obse", None):
                        existente.said_obse = f"Devolução NF {getattr(nota, 'numero', '')}"
                    existente.save(using=self.banco)
                else:
                    seq += 1
                    SaidasEstoque.objects.using(self.banco).create(
                        said_sequ=seq,
                        said_empr=int(empresa),
                        said_fili=int(filial),
                        said_prod=prod,
                        said_enti=str(entidade_id),
                        said_data=mov_data,
                        said_quan=qtd,
                        said_tota=total,
                        said_obse=f"Devolução NF {getattr(nota, 'numero', '')}",
                        said_usua=int(usuario_id),
                    )
            return

        seq = int(EntradaEstoque.objects.using(self.banco).aggregate(max_sequ=Max("entr_sequ")).get("max_sequ") or 0)
        for item in itens_payload:
            prod = str(item.get("produto") or "").strip()
            if not prod:
                continue
            qtd = self._to_qty(Decimal(str(item.get("quantidade") or 0)))
            if qtd <= 0:
                continue
            unit = Decimal(str(item.get("unitario") or 0))
            desc = Decimal(str(item.get("desconto") or 0))
            total = self._to_money((qtd * unit) - desc)
            existente = (
                EntradaEstoque.objects.using(self.banco)
                .filter(entr_empr=int(empresa), entr_fili=int(filial), entr_prod=prod, entr_data=mov_data)
                .first()
            )
            if existente:
                existente.entr_quan = self._to_qty(Decimal(str(existente.entr_quan or 0)) + qtd)
                existente.entr_tota = self._to_money(Decimal(str(existente.entr_tota or 0)) + total)
                if not getattr(existente, "entr_enti", None):
                    existente.entr_enti = str(entidade_id)
                if not getattr(existente, "entr_usua", None):
                    existente.entr_usua = int(usuario_id)
                if not getattr(existente, "entr_obse", None):
                    existente.entr_obse = f"Devolução NF {getattr(nota, 'numero', '')}"
                existente.save(using=self.banco)
            else:
                seq += 1
                EntradaEstoque.objects.using(self.banco).create(
                    entr_sequ=seq,
                    entr_empr=int(empresa),
                    entr_fili=int(filial),
                    entr_prod=prod,
                    entr_enti=str(entidade_id),
                    entr_data=mov_data,
                    entr_quan=qtd,
                    entr_tota=total,
                    entr_obse=f"Devolução NF {getattr(nota, 'numero', '')}",
                    entr_usua=int(usuario_id),
                )

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
