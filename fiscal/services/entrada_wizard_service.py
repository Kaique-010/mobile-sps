from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


class EntradaWizardService:
    def __init__(self, *, banco: str):
        self.banco = banco or "default"

    def iniciar(
        self,
        *,
        documento_id: int,
        empresa: int,
        filial: int,
        data_entrada: date | None = None,
    ):
        from fiscal.models import NFeDocumento
        from Entidades.models import Entidades
        from Entidades.utils import proxima_entidade
        from NotasDestinadas.models import NotaFiscalEntrada

        doc = (
            NFeDocumento.objects.using(self.banco)
            .filter(pk=int(documento_id), empresa=int(empresa), filial=int(filial))
            .first()
        )
        if not doc:
            raise ValidationError("Documento não encontrado.")

        payload = doc.json_dict or {}
        ide = payload.get("ide") or {}
        emit = payload.get("emitente") or {}
        dest = payload.get("destinatario") or {}
        total = payload.get("total") or {}

        numero = _to_int(ide.get("nNF"))
        serie_raw = str(ide.get("serie") or "").strip()
        serie = serie_raw or "1"
        modelo = str(ide.get("mod") or "").strip()
        natop = str(ide.get("natOp") or "").strip()
        tp_nf = _to_int(ide.get("tpNF"))

        if numero is None:
            raise ValidationError("Não foi possível identificar número da NF no XML.")

        data_emissao = _parse_date(ide.get("dhEmi")) or _parse_date(ide.get("dEmi"))
        if not data_emissao:
            data_emissao = date.today()

        if data_entrada is None:
            data_entrada = date.today()

        defaults = {
            "empresa": int(empresa),
            "filial": int(filial),
            "xml_nfe": doc.xml_original,
            "status_nfe": 100,
            "cancelada": False,
            "denegada": False,
            "inutilizada": False,
            "natureza_operacao": natop or None,
            "modelo": modelo or None,
            "serie": serie,
            "numero_nota_fiscal": int(numero),
            "data_emissao": data_emissao,
            "data_saida_entrada": data_entrada,
            "tipo_operacao": tp_nf,
            "emitente_cnpj": _only_digits(emit.get("cnpj")) or None,
            "emitente_cpf": _only_digits(emit.get("cpf")) or None,
            "emitente_razao_social": (emit.get("nome") or "").strip() or None,
            "emitente_nome_fantasia": (emit.get("fantasia") or "").strip() or None,
            "emitente_ie": (emit.get("ie") or "").strip() or None,
            "destinatario_cnpj": _only_digits(dest.get("cnpj")) or None,
            "destinatario_cpf": _only_digits(dest.get("cpf")) or None,
            "destinatario_razao_social": (dest.get("nome") or "").strip() or None,
            "destinatario_ie": (dest.get("ie") or "").strip() or None,
            "valor_total_nota": _to_decimal(total.get("vNF")),
            "valor_total_produtos": _to_decimal(total.get("vProd")),
            "valor_total_desconto": _to_decimal(total.get("vDesc")),
        }

        emit_ender = (emit.get("ender") or {}) if isinstance(emit.get("ender"), dict) else {}
        dest_ender = (dest.get("ender") or {}) if isinstance(dest.get("ender"), dict) else {}

        defaults.update(
            {
                "emitente_logradouro": (emit_ender.get("xLgr") or "").strip() or None,
                "emitente_numero": (emit_ender.get("nro") or "").strip() or None,
                "emitente_bairro": (emit_ender.get("xBairro") or "").strip() or None,
                "emitente_nome_municipio": (emit_ender.get("xMun") or "").strip() or None,
                "emitente_uf": (emit_ender.get("UF") or "").strip().upper() or None,
                "emitente_cep": _to_int(_only_digits(emit_ender.get("CEP"))) if emit_ender.get("CEP") else None,
                "emitente_fone": _only_digits(emit_ender.get("fone")) or None,
                "destinatario_logradouro": (dest_ender.get("xLgr") or "").strip() or None,
                "destinatario_numero": (dest_ender.get("nro") or "").strip() or None,
                "destinatario_bairro": (dest_ender.get("xBairro") or "").strip() or None,
                "destinatario_nome_municipio": (dest_ender.get("xMun") or "").strip() or None,
                "destinatario_uf": (dest_ender.get("UF") or "").strip().upper() or None,
                "destinatario_cep": _to_int(_only_digits(dest_ender.get("CEP"))) if dest_ender.get("CEP") else None,
                "destinatario_fone": _only_digits(dest_ender.get("fone")) or None,
            }
        )

        nota = None
        if not serie_raw:
            try:
                existente = (
                    NotaFiscalEntrada.objects.using(self.banco)
                    .filter(empresa=int(empresa), filial=int(filial), numero_nota_fiscal=int(numero))
                    .filter(serie__in=["", None])
                    .first()
                )
            except Exception:
                existente = None
            if existente:
                for k, v in defaults.items():
                    setattr(existente, k, v)
                try:
                    existente.serie = serie
                except Exception:
                    pass
                existente.save(using=self.banco)
                nota = existente

        if nota is None:
            nota, _created = NotaFiscalEntrada.objects.using(self.banco).update_or_create(
                empresa=int(empresa),
                filial=int(filial),
                numero_nota_fiscal=int(numero),
                serie=serie,
                defaults=defaults,
            )

        fornecedor = None
        doc_digits = _only_digits(emit.get("cnpj") or emit.get("cpf") or emit.get("documento") or "")
        if doc_digits:
            qs = Entidades.objects.using(self.banco).filter(enti_empr=int(empresa))
            if len(doc_digits) == 14:
                fornecedor = qs.filter(enti_cnpj=doc_digits).first()
            elif len(doc_digits) == 11:
                fornecedor = qs.filter(enti_cpf=doc_digits).first()

        if not fornecedor:
            emit_nome = (emit.get("nome") or emit.get("fantasia") or "").strip() or "FORNECEDOR"
            emit_ender = (emit.get("ender") or {}) if isinstance(emit.get("ender"), dict) else {}
            cep = _only_digits(emit_ender.get("CEP"))[:8] or "00000000"
            ende = (emit_ender.get("xLgr") or "").strip()[:60] or "SEM ENDERECO"
            nume = (emit_ender.get("nro") or "").strip()[:10] or "S/N"
            bair = (emit_ender.get("xBairro") or "").strip()[:60] or "CENTRO"
            cida = (emit_ender.get("xMun") or "").strip()[:60] or "NAO INFORMADO"
            uf = (emit_ender.get("UF") or "").strip().upper()[:2] or "ZZ"
            fone = _only_digits(emit_ender.get("fone"))[:14] or None
            ie = str(emit.get("ie") or "").strip()[:14] or None

            proximo = proxima_entidade(int(empresa), int(filial), self.banco)
            fornecedor = Entidades.objects.using(self.banco).create(
                enti_empr=int(empresa),
                enti_clie=int(proximo),
                enti_nome=emit_nome[:100],
                enti_tipo_enti="FO",
                enti_fant=(emit.get("fantasia") or emit_nome)[:100],
                enti_cnpj=doc_digits if len(doc_digits) == 14 else None,
                enti_cpf=doc_digits if len(doc_digits) == 11 else None,
                enti_insc_esta=ie,
                enti_cep=cep,
                enti_ende=ende,
                enti_nume=nume,
                enti_cida=cida,
                enti_esta=uf,
                enti_bair=bair,
                enti_comp=None,
                enti_fone=fone,
                enti_emai=None,
                enti_tien="E",
                enti_situ="1",
            )

        try:
            nota.cliente = int(getattr(fornecedor, "enti_clie", 0) or 0) or None
            nota.save(using=self.banco)
        except Exception:
            pass

        return nota

    def itens_preprocessar(self, *, nota_id: int):
        from NotasDestinadas.models import NotaFiscalEntrada
        from Produtos.models import Produtos
        from NotasDestinadas.services.entrada_nfe_service import EntradaNFeService

        nota = NotaFiscalEntrada.objects.using(self.banco).filter(pk=int(nota_id)).first()
        if not nota:
            raise ValidationError("Entrada (nfev) não encontrada.")

        itens = EntradaNFeService.listar_itens(nota_entrada=nota) or []
        sugeridos = []
        for it in itens:
            if not isinstance(it, dict):
                continue
            prod = None
            if it.get("ean"):
                prod = (
                    Produtos.objects.using(self.banco)
                    .filter(prod_coba=it["ean"], prod_empr=str(nota.empresa))
                    .first()
                )
            if not prod and it.get("forn_cod"):
                prod = (
                    Produtos.objects.using(self.banco)
                    .filter(prod_codi=it["forn_cod"], prod_empr=str(nota.empresa))
                    .first()
                )
            su = dict(it)
            su["produto_sugerido"] = str(getattr(prod, "prod_codi", "") or "") or None
            su["produto_nome"] = str(getattr(prod, "prod_nome", "") or "") or None
            sugeridos.append(su)

        return {"nota_id": int(nota_id), "empresa": nota.empresa, "filial": nota.filial, "itens": sugeridos}

    def financeiro_preview(self, *, nota_id: int):
        from NotasDestinadas.models import NotaFiscalEntrada
        from NotasDestinadas.services.entrada_nfe_service import EntradaNFeService

        nota = NotaFiscalEntrada.objects.using(self.banco).filter(pk=int(nota_id)).first()
        if not nota:
            raise ValidationError("Entrada (nfev) não encontrada.")

        duplicatas = EntradaNFeService._extrair_duplicatas(nota.xml_nfe or "")
        out = []
        for d in duplicatas or []:
            out.append(
                {
                    "numero": str(d.get("numero") or "").strip(),
                    "vencimento": getattr(d.get("vencimento"), "isoformat", lambda: "")(),
                    "valor": str(d.get("valor") or ""),
                }
            )

        return {
            "nota_id": int(nota_id),
            "empresa": nota.empresa,
            "filial": nota.filial,
            "numero_nota_fiscal": nota.numero_nota_fiscal,
            "serie": nota.serie,
            "data_emissao": nota.data_emissao.isoformat() if nota.data_emissao else None,
            "data_entrada": nota.data_saida_entrada.isoformat() if nota.data_saida_entrada else None,
            "valor_total_nota": str(nota.valor_total_nota or ""),
            "duplicatas": out,
        }

    def auto_mapear(self, *, nota_id: int, itens: list) -> dict:
        from NotasDestinadas.models import NotaFiscalEntrada
        from Produtos.models import Produtos

        nota = NotaFiscalEntrada.objects.using(self.banco).filter(pk=int(nota_id)).first()
        if not nota:
            raise ValidationError("Entrada (nfev) não encontrada.")

        empresa_str = str(nota.empresa)
        itens_list = itens or []
        if not isinstance(itens_list, list):
            raise ValidationError("Itens inválidos.")

        out = []
        for it in itens_list:
            if not isinstance(it, dict):
                continue
            prod_atual = str(it.get("prod") or "").strip()
            if prod_atual:
                out.append(dict(it))
                continue

            ean = str(it.get("ean") or "").strip()
            forn_cod = str(it.get("forn_cod") or "").strip()

            prod = None
            if ean and ean.upper() != "SEM GTIN":
                prod = (
                    Produtos.objects.using(self.banco)
                    .filter(prod_empr=empresa_str)
                    .filter(prod_gtin=ean)
                    .first()
                    or Produtos.objects.using(self.banco).filter(prod_empr=empresa_str, prod_coba=ean).first()
                )
            if not prod and forn_cod:
                prod = Produtos.objects.using(self.banco).filter(prod_empr=empresa_str, prod_codi=forn_cod).first()

            item_out = dict(it)
            item_out["produto_sugerido"] = str(getattr(prod, "prod_codi", "") or "") or None
            item_out["produto_nome"] = str(getattr(prod, "prod_nome", "") or "") or None
            out.append(item_out)

        return {"nota_id": int(nota_id), "empresa": nota.empresa, "filial": nota.filial, "itens": out}

    def criar_produtos_faltantes(self, *, nota_id: int, itens: list, usuario_id: int = 0) -> dict:
        from NotasDestinadas.models import NotaFiscalEntrada
        from Produtos.models import Produtos, UnidadeMedida

        nota = NotaFiscalEntrada.objects.using(self.banco).filter(pk=int(nota_id)).first()
        if not nota:
            raise ValidationError("Entrada (nfev) não encontrada.")

        empresa_str = str(nota.empresa)
        itens_list = itens or []
        if not isinstance(itens_list, list):
            raise ValidationError("Itens inválidos.")

        criados = []
        atualizados = []

        for idx, it in enumerate(itens_list):
            if not isinstance(it, dict):
                continue
            prod_atual = str(it.get("prod") or "").strip()
            if prod_atual:
                atualizados.append(dict(it))
                continue

            descricao = str(it.get("descricao") or "").strip()
            unidade = str(it.get("unidade") or "UN").strip() or "UN"
            ncm = str(it.get("ncm") or "").strip()
            ean = str(it.get("ean") or "").strip()
            forn_cod = str(it.get("forn_cod") or "").strip()

            if not descricao:
                atualizados.append(dict(it))
                continue

            un_obj = UnidadeMedida.objects.using(self.banco).filter(unid_codi=unidade).first()
            if not un_obj:
                try:
                    un_obj = UnidadeMedida.objects.using(self.banco).create(unid_codi=unidade, unid_desc=unidade)
                except Exception:
                    un_obj = UnidadeMedida.objects.using(self.banco).filter(unid_codi="UN").first()
            if not un_obj:
                raise ValidationError(f"Unidade não encontrada: {unidade}")

            codigo = forn_cod
            if codigo:
                existente = Produtos.objects.using(self.banco).filter(prod_empr=empresa_str, prod_codi=codigo).first()
                if existente:
                    atualizados.append({**dict(it), "prod": existente.prod_codi})
                    continue
            else:
                codigo = self._proximo_codigo_produto(empresa_str)

            novo = Produtos.objects.using(self.banco).create(
                prod_empr=empresa_str,
                prod_codi=codigo,
                prod_codi_nume=codigo,
                prod_nome=descricao[:255],
                prod_unme=un_obj,
                prod_ncm=ncm[:8] if ncm else "",
                prod_coba=ean if ean and ean.upper() != "SEM GTIN" else "",
                prod_gtin=ean if ean and ean.upper() != "SEM GTIN" else "SEM GTIN",
            )
            criados.append({"index": idx, "codigo": novo.prod_codi})
            atualizados.append({**dict(it), "prod": novo.prod_codi})

        return {"nota_id": int(nota_id), "criados": criados, "itens": atualizados}

    def finalizar(
        self,
        *,
        nota_id: int,
        entradas: list,
        usuario_id: int = 0,
        parcelas: list | None = None,
        forma_pagamento: str | None = None,
    ) -> dict:
        from NotasDestinadas.models import NotaFiscalEntrada
        from NotasDestinadas.services.entrada_nfe_service import EntradaNFeService

        nota = NotaFiscalEntrada.objects.using(self.banco).filter(pk=int(nota_id)).first()
        if not nota:
            raise ValidationError("Entrada (nfev) não encontrada.")

        entradas_list = entradas or []
        if not isinstance(entradas_list, list):
            raise ValidationError("Entradas inválidas.")

        duplicatas_override = None
        if parcelas is not None:
            if not isinstance(parcelas, list):
                raise ValidationError("Parcelas inválidas.")
            duplicatas_override = []
            for p in parcelas:
                if not isinstance(p, dict):
                    continue
                numero = str(p.get("numero") or "").strip()
                venc = _parse_date(p.get("vencimento"))
                valor = _to_decimal(p.get("valor"))
                if not venc or valor is None:
                    raise ValidationError("Cada parcela precisa de vencimento e valor.")
                duplicatas_override.append({"numero": numero, "vencimento": venc, "valor": valor})

        return EntradaNFeService.confirmar_processamento(
            nota_entrada=nota,
            entradas=entradas_list,
            banco=self.banco,
            usuario_id=int(usuario_id or 0),
            duplicatas_override=duplicatas_override,
            forma_pagamento=(str(forma_pagamento or "").strip() or None),
        )

    def _proximo_codigo_produto(self, empresa_str: str) -> str:
        from Produtos.models import Produtos

        ultimo = Produtos.objects.using(self.banco).filter(prod_empr=empresa_str).order_by("-prod_codi").first()
        try:
            proximo = int(getattr(ultimo, "prod_codi", "0")) + 1 if (ultimo and str(getattr(ultimo, "prod_codi", "")).isdigit()) else 1
        except Exception:
            proximo = 1
        while Produtos.objects.using(self.banco).filter(prod_empr=empresa_str, prod_codi=str(proximo)).exists():
            proximo += 1
        return str(proximo)


def _parse_date(value) -> date | None:
    s = str(value or "").strip()
    if not s:
        return None
    s = s.replace("Z", "")
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date()
        except Exception:
            pass
    try:
        dt = datetime.fromisoformat(s)
        return dt.date()
    except Exception:
        return None


def _only_digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _to_int(value):
    try:
        s = str(value or "").strip()
        if not s:
            return None
        return int(float(s))
    except Exception:
        return None


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None
