from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import logging

from django.db import transaction
from django.db.models import Max

from contas_a_receber.models import Titulosreceber
from contas_a_receber.services import criar_titulo_receber, gera_parcelas_a_receber

from .models import Caixageral, Movicaixa, TIPO_MOVIMENTO


logger = logging.getLogger(__name__)


class CaixaService:
    @staticmethod
    def resolver_tipo_movimento(*, movi_tipo=None, forma_pagamento=None):
        if movi_tipo not in [None, "", 0, "0"]:
            return str(movi_tipo)
        if forma_pagamento not in [None, "", 0, "0"]:
            return {
                "51": "3",
                "52": "4",
                "54": "1",
                "60": "6",
            }.get(str(forma_pagamento))
        return None

    @staticmethod
    def _to_int(value, default=None):
        if value in [None, ""]:
            return default
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _to_decimal(value, default=Decimal("0")):
        if value in [None, ""]:
            return default
        try:
            return Decimal(str(value))
        except Exception:
            return default

    @staticmethod
    def _map_titulo_forma_recebimento(tipo_movimento: str | None, forma_pagamento=None) -> str:
        if forma_pagamento not in [None, "", 0, "0"]:
            fp = str(forma_pagamento)
            if fp in {"51", "52", "54", "60"}:
                return fp
        return {
            "1": "54",
            "2": "01",
            "3": "51",
            "4": "52",
            "5": "00",
            "6": "60",
        }.get(str(tipo_movimento or ""), "54")

    @staticmethod
    def _add_months(d: date, m: int) -> date:
        from calendar import monthrange

        y = d.year + (d.month - 1 + m) // 12
        mo = (d.month - 1 + m) % 12 + 1
        last = monthrange(y, mo)[1]
        day = d.day if d.day <= last else last
        return date(y, mo, day)

    @staticmethod
    def processar_pagamento_venda(
        *,
        banco: str,
        empresa_id,
        filial_id,
        numero_venda,
        valor,
        cliente=None,
        vendedor=None,
        forma_pagamento=None,
        movi_tipo=None,
        valor_pago=None,
        troco=None,
        parcelas=1,
        operador=None,
    ):
        tipo_movimento = CaixaService.resolver_tipo_movimento(movi_tipo=movi_tipo, forma_pagamento=forma_pagamento)

        if not numero_venda or valor in [None, ""]:
            raise ValueError("Número da venda e valor são obrigatórios")

        if not tipo_movimento:
            raise ValueError("Forma de pagamento inválida")

        tipos_validos = {"1", "2", "3", "4", "5", "6"}
        if str(tipo_movimento) not in tipos_validos:
            raise ValueError(f"Tipo de movimento inválido. Opções válidas: {sorted(list(tipos_validos))}")

        empresa_int = CaixaService._to_int(empresa_id)
        filial_int = CaixaService._to_int(filial_id)
        if empresa_int is None or filial_int is None:
            raise ValueError("Empresa e Filial são obrigatórios")

        parcelas_int = CaixaService._to_int(parcelas, default=1) or 1
        parcelas_str = str(parcelas_int)

        num_venda_str = str(numero_venda)
        titulo_numero = num_venda_str[:13]
        titulo_serie = "CAI"

        valor_decimal = CaixaService._to_decimal(valor)
        valor_pago_decimal = CaixaService._to_decimal(valor_pago, default=valor_decimal)
        troco_decimal = CaixaService._to_decimal(troco, default=Decimal("0"))
        troco_decimal = troco_decimal if troco_decimal > 0 else Decimal("0")

        forma_pagamento_int = CaixaService._to_int(forma_pagamento)
        vendedor_int = CaixaService._to_int(vendedor)
        cliente_int = CaixaService._to_int(cliente)
        operador_int = CaixaService._to_int(operador)

        if cliente_int is None or vendedor_int is None:
            try:
                from Pedidos.models import PedidoVenda
            except Exception:
                PedidoVenda = None

            if PedidoVenda is not None:
                pedido = (
                    PedidoVenda.objects.using(banco)
                    .filter(
                        pedi_empr=empresa_int,
                        pedi_fili=filial_int,
                        pedi_nume=str(numero_venda),
                    )
                    .first()
                )
                if pedido:
                    if cliente_int is None:
                        cliente_int = CaixaService._to_int(getattr(pedido, "pedi_forn", None))
                    if vendedor_int is None:
                        vendedor_int = CaixaService._to_int(getattr(pedido, "pedi_vend", None))

        logger.info(
            "CaixaService.processar_pagamento_venda chamado banco=%s empr=%s fili=%s venda=%s tipo=%s forma=%s parcelas=%s cliente=%s vendedor=%s",
            banco,
            empresa_int,
            filial_int,
            numero_venda,
            tipo_movimento,
            forma_pagamento,
            parcelas_int,
            cliente_int,
            vendedor_int,
        )

        with transaction.atomic(using=banco):
            caixa_aberto = (
                Caixageral.objects.using(banco)
                .filter(caix_empr=empresa_int, caix_fili=filial_int, caix_aber="A")
                .first()
            )
            if not caixa_aberto:
                raise ValueError("Nenhum caixa aberto encontrado")

            ultimo_ctrl = (
                Movicaixa.objects.using(banco)
                .filter(movi_empr=empresa_int, movi_fili=filial_int, movi_data=caixa_aberto.caix_data)
                .aggregate(Max("movi_ctrl"))["movi_ctrl__max"]
                or 0
            )

            mov = Movicaixa.objects.using(banco).create(
                movi_empr=empresa_int,
                movi_fili=filial_int,
                movi_caix=caixa_aberto.caix_caix,
                movi_nume_vend=CaixaService._to_int(numero_venda, default=0) or numero_venda,
                movi_tipo=CaixaService._to_int(tipo_movimento, default=0) or tipo_movimento,
                movi_tipo_movi=forma_pagamento_int,
                movi_vend=vendedor_int,
                movi_clie=cliente_int,
                movi_entr=valor_pago_decimal,
                movi_said=troco_decimal,
                movi_obse=f"Venda {num_venda_str}, Pagamento {dict(TIPO_MOVIMENTO).get(str(tipo_movimento))} - Parcelas: {parcelas_str}",
                movi_data=caixa_aberto.caix_data,
                movi_hora=datetime.now().time(),
                movi_ctrl=int(ultimo_ctrl) + 1,
                movi_oper=operador_int,
                movi_parc=parcelas_str,
                movi_titu=titulo_numero,
                movi_seri=titulo_serie,
            )

            titulo_criado = None
            tipo_mov_str = str(tipo_movimento)
            if tipo_mov_str == "5":
                if cliente_int is None:
                    raise ValueError("Cliente é obrigatório para gerar título a receber no crediário")

                existentes = set(
                    Titulosreceber.objects.using(banco)
                    .filter(
                        titu_empr=empresa_int,
                        titu_fili=filial_int,
                        titu_clie=cliente_int,
                        titu_titu=titulo_numero,
                        titu_seri=titulo_serie,
                    )
                    .values_list("titu_parc", flat=True)
                )

                n = max(parcelas_int, 1)
                total = Decimal(str(valor_decimal or 0))
                base = (total / Decimal(n)).quantize(Decimal("0.01"))
                dif = total - (base * n)
                criadas = 0
                for i in range(1, n + 1):
                    parc = str(i)
                    if parc in existentes:
                        continue
                    v = base if i < n else base + dif
                    dados = {
                        "titu_empr": empresa_int,
                        "titu_fili": filial_int,
                        "titu_clie": cliente_int,
                        "titu_titu": titulo_numero,
                        "titu_seri": titulo_serie,
                        "titu_parc": parc,
                        "titu_emis": caixa_aberto.caix_data,
                        "titu_venc": CaixaService._add_months(caixa_aberto.caix_data, i),
                        "titu_valo": v,
                        "titu_hist": f"Venda {num_venda_str} - Gerado pelo Caixa",
                        "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento, forma_pagamento),
                        "titu_vend": vendedor_int,
                        "titu_situ": 1,
                        "titu_aber": "A",
                        "titu_tipo": "Receber",
                    }
                    titulo_criado = criar_titulo_receber(
                        banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                    )
                    criadas += 1
                logger.info(
                    "CaixaService.processar_pagamento_venda criou parcelas=%s titulo=%s serie=%s cliente=%s",
                    criadas,
                    titulo_numero,
                    titulo_serie,
                    cliente_int,
                )
            elif tipo_mov_str in {"2", "3", "4"}:
                cliente_titulo = cliente_int if cliente_int is not None else 1

                existentes = set(
                    Titulosreceber.objects.using(banco)
                    .filter(
                        titu_empr=empresa_int,
                        titu_fili=filial_int,
                        titu_clie=cliente_titulo,
                        titu_titu=titulo_numero,
                        titu_seri=titulo_serie,
                    )
                    .values_list("titu_parc", flat=True)
                )

                n = max(parcelas_int, 1)
                total = Decimal(str(valor_decimal or 0))
                base = (total / Decimal(n)).quantize(Decimal("0.01"))
                dif = total - (base * n)
                criadas = 0
                for i in range(1, n + 1):
                    parc = str(i)
                    if parc in existentes:
                        continue
                    v = base if i < n else base + dif
                    dados = {
                        "titu_empr": empresa_int,
                        "titu_fili": filial_int,
                        "titu_clie": cliente_titulo,
                        "titu_titu": titulo_numero,
                        "titu_seri": titulo_serie,
                        "titu_parc": parc,
                        "titu_emis": caixa_aberto.caix_data,
                        "titu_venc": CaixaService._add_months(caixa_aberto.caix_data, i),
                        "titu_valo": v,
                        "titu_hist": f"Venda {num_venda_str} - Gerado pelo Caixa",
                        "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento, forma_pagamento),
                        "titu_vend": vendedor_int,
                        "titu_situ": 1,
                        "titu_aber": "A",
                        "titu_tipo": "Receber",
                    }
                    titulo_criado = criar_titulo_receber(
                        banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                    )
                    criadas += 1

                logger.info(
                    "CaixaService.processar_pagamento_venda criou titulos a receber parcelas=%s titulo=%s serie=%s cliente=%s tipo=%s",
                    criadas,
                    titulo_numero,
                    titulo_serie,
                    cliente_titulo,
                    tipo_mov_str,
                )
            elif tipo_mov_str in {"1", "6"}:
                cliente_titulo = cliente_int if cliente_int is not None else 1
                existe = (
                    Titulosreceber.objects.using(banco)
                    .filter(
                        titu_empr=empresa_int,
                        titu_fili=filial_int,
                        titu_clie=cliente_titulo,
                        titu_titu=titulo_numero,
                        titu_seri=titulo_serie,
                        titu_parc="1",
                    )
                    .exists()
                )
                if not existe:
                    dados = {
                        "titu_empr": empresa_int,
                        "titu_fili": filial_int,
                        "titu_clie": cliente_titulo,
                        "titu_titu": titulo_numero,
                        "titu_seri": titulo_serie,
                        "titu_parc": "1",
                        "titu_emis": caixa_aberto.caix_data,
                        "titu_venc": caixa_aberto.caix_data,
                        "titu_valo": Decimal(str(valor_decimal or 0)),
                        "titu_hist": f"Venda {num_venda_str} - Recebido no Caixa",
                        "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento, forma_pagamento),
                        "titu_vend": vendedor_int,
                        "titu_situ": 1,
                        "titu_aber": "T",
                        "titu_tipo": "Receber",
                    }
                    titulo_criado = criar_titulo_receber(
                        banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                    )
                    logger.info(
                        "CaixaService.processar_pagamento_venda criou titulo recebido titulo=%s serie=%s cliente=%s tipo=%s",
                        titulo_numero,
                        titulo_serie,
                        cliente_titulo,
                        tipo_mov_str,
                    )
                else:
                    logger.info(
                        "CaixaService.processar_pagamento_venda titulo recebido já existe titulo=%s serie=%s cliente=%s tipo=%s",
                        titulo_numero,
                        titulo_serie,
                        cliente_titulo,
                        tipo_mov_str,
                    )
            else:
                logger.info(
                    "CaixaService.processar_pagamento_venda não cria titulo para tipo=%s titulo=%s serie=%s",
                    tipo_mov_str,
                    titulo_numero,
                    titulo_serie,
                )

            return mov, titulo_criado

    @staticmethod
    def criar_lancamento_caixa(
        *,
        banco: str,
        empresa_id,
        filial_id,
        tipo,
        valor,
        forma=None,
        observacao="",
        operador=None,
        cliente=None,
        vendedor=None,
        titulo=None,
        serie=None,
        parcelas=1,
    ):
        if not tipo or tipo not in ["entrada", "saida"]:
            raise ValueError("Tipo inválido")

        valor_decimal = CaixaService._to_decimal(valor)
        if valor_decimal <= 0:
            raise ValueError("Valor deve ser maior que zero")

        mapa = {
            "dinheiro": "1",
            "cheque": "2",
            "credito": "3",
            "crédito": "3",
            "debito": "4",
            "débito": "4",
            "crediario": "5",
            "crediário": "5",
            "pix": "6",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
        }
        forma_key = (str(forma or "").strip().lower() or "dinheiro")
        tipo_movimento = mapa.get(forma_key)
        if not tipo_movimento:
            raise ValueError("Forma de pagamento inválida")

        empresa_int = CaixaService._to_int(empresa_id)
        filial_int = CaixaService._to_int(filial_id)
        if empresa_int is None or filial_int is None:
            raise ValueError("Empresa e Filial são obrigatórios")

        operador_int = CaixaService._to_int(operador)
        cliente_int = CaixaService._to_int(cliente)
        vendedor_int = CaixaService._to_int(vendedor)

        parcelas_int = CaixaService._to_int(parcelas, default=1) or 1
        parcelas_str = str(parcelas_int)

        serie_str = (str(serie).strip() if serie not in [None, ""] else "CAI")[:5]
        titulo_str = (str(titulo).strip() if titulo not in [None, ""] else "")[:13] or None

        with transaction.atomic(using=banco):
            caixa_aberto = (
                Caixageral.objects.using(banco)
                .filter(caix_empr=empresa_int, caix_fili=filial_int, caix_aber="A")
                .first()
            )
            if not caixa_aberto:
                raise ValueError("Nenhum caixa aberto encontrado")

            ultimo_ctrl = (
                Movicaixa.objects.using(banco)
                .filter(movi_empr=empresa_int, movi_fili=filial_int, movi_data=caixa_aberto.caix_data)
                .aggregate(Max("movi_ctrl"))["movi_ctrl__max"]
                or 0
            )
            prox_ctrl = int(ultimo_ctrl) + 1

            if not titulo_str:
                titulo_str = f"{caixa_aberto.caix_data.strftime('%y%m%d')}{str(prox_ctrl).zfill(7)}"

            mov = Movicaixa.objects.using(banco).create(
                movi_empr=empresa_int,
                movi_fili=filial_int,
                movi_caix=caixa_aberto.caix_caix,
                movi_data=caixa_aberto.caix_data,
                movi_ctrl=prox_ctrl,
                movi_tipo=CaixaService._to_int(tipo_movimento, default=0) or tipo_movimento,
                movi_tipo_movi=CaixaService._to_int(tipo_movimento, default=0) or tipo_movimento,
                movi_entr=valor_decimal if tipo == "entrada" else Decimal("0"),
                movi_said=valor_decimal if tipo == "saida" else Decimal("0"),
                movi_obse=observacao or f"Lancamento {tipo}",
                movi_hora=datetime.now().time(),
                movi_oper=operador_int,
                movi_titu=titulo_str,
                movi_seri=serie_str,
                movi_parc=parcelas_str,
                movi_clie=cliente_int,
                movi_vend=vendedor_int,
            )

            titulo_criado = None
            if tipo == "entrada":
                tipo_mov_str = str(tipo_movimento)
                if tipo_mov_str == "5":
                    if cliente_int is None:
                        raise ValueError("Cliente é obrigatório para gerar título a receber no crediário")

                    existentes = set(
                        Titulosreceber.objects.using(banco)
                        .filter(
                            titu_empr=empresa_int,
                            titu_fili=filial_int,
                            titu_clie=cliente_int,
                            titu_titu=titulo_str,
                            titu_seri=serie_str,
                        )
                        .values_list("titu_parc", flat=True)
                    )

                    n = max(parcelas_int, 1)
                    total = Decimal(str(valor_decimal or 0))
                    base = (total / Decimal(n)).quantize(Decimal("0.01"))
                    dif = total - (base * n)
                    for i in range(1, n + 1):
                        parc = str(i)
                        if parc in existentes:
                            continue
                        v = base if i < n else base + dif
                        dados = {
                            "titu_empr": empresa_int,
                            "titu_fili": filial_int,
                            "titu_clie": cliente_int,
                            "titu_titu": titulo_str,
                            "titu_seri": serie_str,
                            "titu_parc": parc,
                            "titu_emis": caixa_aberto.caix_data,
                            "titu_venc": CaixaService._add_months(caixa_aberto.caix_data, i),
                            "titu_valo": v,
                            "titu_hist": (observacao or f"Lancamento {tipo}").strip(),
                            "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento),
                            "titu_vend": vendedor_int,
                            "titu_situ": 1,
                            "titu_aber": "A",
                            "titu_tipo": "Receber",
                        }
                        titulo_criado = criar_titulo_receber(
                            banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                        )
                elif tipo_mov_str in {"2", "3", "4"}:
                    cliente_titulo = cliente_int if cliente_int is not None else 1

                    existentes = set(
                        Titulosreceber.objects.using(banco)
                        .filter(
                            titu_empr=empresa_int,
                            titu_fili=filial_int,
                            titu_clie=cliente_titulo,
                            titu_titu=titulo_str,
                            titu_seri=serie_str,
                        )
                        .values_list("titu_parc", flat=True)
                    )

                    n = max(parcelas_int, 1)
                    total = Decimal(str(valor_decimal or 0))
                    base = (total / Decimal(n)).quantize(Decimal("0.01"))
                    dif = total - (base * n)
                    for i in range(1, n + 1):
                        parc = str(i)
                        if parc in existentes:
                            continue
                        v = base if i < n else base + dif
                        dados = {
                            "titu_empr": empresa_int,
                            "titu_fili": filial_int,
                            "titu_clie": cliente_titulo,
                            "titu_titu": titulo_str,
                            "titu_seri": serie_str,
                            "titu_parc": parc,
                            "titu_emis": caixa_aberto.caix_data,
                            "titu_venc": CaixaService._add_months(caixa_aberto.caix_data, i),
                            "titu_valo": v,
                            "titu_hist": (observacao or f"Lancamento {tipo}").strip(),
                            "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento),
                            "titu_vend": vendedor_int,
                            "titu_situ": 1,
                            "titu_aber": "A",
                            "titu_tipo": "Receber",
                        }
                        titulo_criado = criar_titulo_receber(
                            banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                        )
                elif tipo_mov_str in {"1", "6"}:
                    cliente_titulo = cliente_int if cliente_int is not None else 1
                    existe = (
                        Titulosreceber.objects.using(banco)
                        .filter(
                            titu_empr=empresa_int,
                            titu_fili=filial_int,
                            titu_clie=cliente_titulo,
                            titu_titu=titulo_str,
                            titu_seri=serie_str,
                            titu_parc="1",
                        )
                        .exists()
                    )
                    if not existe:
                        dados = {
                            "titu_empr": empresa_int,
                            "titu_fili": filial_int,
                            "titu_clie": cliente_titulo,
                            "titu_titu": titulo_str,
                            "titu_seri": serie_str,
                            "titu_parc": "1",
                            "titu_emis": caixa_aberto.caix_data,
                            "titu_venc": caixa_aberto.caix_data,
                            "titu_valo": Decimal(str(valor_decimal or 0)),
                            "titu_hist": (observacao or f"Lancamento {tipo}").strip(),
                            "titu_form_reci": CaixaService._map_titulo_forma_recebimento(tipo_movimento),
                            "titu_vend": vendedor_int,
                            "titu_situ": 1,
                            "titu_aber": "T",
                            "titu_tipo": "Receber",
                        }
                        titulo_criado = criar_titulo_receber(
                            banco=banco, dados=dados, empresa_id=empresa_int, filial_id=filial_int
                        )
                else:
                    logger.info(
                        "CaixaService.criar_lancamento_caixa não cria titulo para tipo=%s titulo=%s serie=%s",
                        tipo_mov_str,
                        titulo_str,
                        serie_str,
                    )
            logger.info(
                "CaixaService.criar_lancamento_caixa finalizado titulo=%s serie=%s tipo=%s valor=%s",
                titulo_str,
                serie_str,
                tipo_movimento,
                str(valor_decimal),
            )
            return mov, titulo_criado
