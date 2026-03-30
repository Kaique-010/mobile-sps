from django.db.models import F, Sum, Max
from django.db import transaction
from decimal import Decimal
from GestaoObras.models import Obra, ObraEtapa, ObraLancamentoFinanceiro, ObraMaterialMovimento, ObraMaterialEstoqueSaldo
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber
from datetime import date, timedelta, datetime


class ObrasService:
    @staticmethod
    def recalcular_saldo_estoque_produto(*, banco: str, obra: Obra, produto: str):
        try:
            prod = (produto or "").strip()
            if not prod:
                return
            qs = (
                ObraMaterialEstoqueSaldo.objects.using(banco)
                .filter(omes_empr=obra.obra_empr, omes_fili=obra.obra_fili, omes_obra_id=obra.id, omes_prod=prod)
                .order_by("omes_data_movi", "id")
            )
            itens = list(qs)
            saldo = Decimal("0")
            for it in itens:
                quan = getattr(it, "omes_quan", None) or Decimal("0")
                tipo = (getattr(it, "omes_tipo", "") or "").strip().upper()
                delta = quan if tipo == "EN" else (-quan)
                saldo = saldo + delta
                it.omes_sald_atua = saldo
            if itens:
                ObraMaterialEstoqueSaldo.objects.using(banco).bulk_update(itens, ["omes_sald_atua"])
        except Exception:
            return

    @staticmethod
    def sincronizar_estoque_movimento_material(*, banco: str, obra: Obra, movimento: ObraMaterialMovimento, movimentar_estoque: bool = True, usuario_id=None):
        try:
            mov_id = getattr(movimento, "id", None)
            if not mov_id:
                return
            produto = (getattr(movimento, "movm_prod", "") or "").strip()
            if not produto:
                return

            if not movimentar_estoque:
                ObraMaterialEstoqueSaldo.objects.using(banco).filter(omes_movm_id=mov_id).delete()
                ObrasService.recalcular_saldo_estoque_produto(banco=banco, obra=obra, produto=produto)
                return

            tipo = (getattr(movimento, "movm_tipo", "") or "").strip().upper()
            if tipo not in {"EN", "SA"}:
                return
            quan = getattr(movimento, "movm_quan", None) or Decimal("0")
            if quan < 0:
                quan = -quan
            unit = getattr(movimento, "movm_cuni", None) or Decimal("0")
            total = quan * unit
            desc = (getattr(movimento, "movm_desc", "") or "").strip()[:255]
            unid = (getattr(movimento, "movm_unid", "") or "").strip()[:6] or "UN"
            docu = (getattr(movimento, "movm_docu", None) or None)
            data_movi = getattr(movimento, "movm_data", None) or date.today()
            etap_id = getattr(movimento, "movm_etap_id", None)
            obse = (getattr(movimento, "movm_obse", "") or "").strip()
            ref = f"movm_id={mov_id} movm_codi={getattr(movimento, 'movm_codi', '')}"
            obse_final = (f"{ref}\n{obse}".strip())[:2000]

            defaults = {
                "omes_empr": obra.obra_empr,
                "omes_fili": obra.obra_fili,
                "omes_obra_id": obra.id,
                "omes_etap_id": etap_id,
                "omes_tipo": tipo,
                "omes_prod": produto,
                "omes_desc": desc,
                "omes_quan": quan,
                "omes_unid": unid,
                "omes_valo_unit": unit,
                "omes_data_movi": data_movi,
                "omes_docu": docu,
                "omes_valo_tota": total,
                "omes_obse": obse_final or None,
                "omes_usua": usuario_id if usuario_id not in ("", None) else None,
            }

            obj, _created = ObraMaterialEstoqueSaldo.objects.using(banco).get_or_create(
                omes_movm_id=mov_id,
                defaults=defaults,
            )
            atualizar = False
            for k, v in defaults.items():
                if getattr(obj, k, None) != v:
                    setattr(obj, k, v)
                    atualizar = True
            if atualizar:
                obj.save(using=banco)
            ObrasService.recalcular_saldo_estoque_produto(banco=banco, obra=obra, produto=produto)
        except Exception:
            return

    @staticmethod
    def consolidar_custo_obra(obra: Obra, banco: str = None) -> Obra:
        qs_mov = ObraMaterialMovimento.objects
        qs_fin = ObraLancamentoFinanceiro.objects
        if banco:
            qs_mov = qs_mov.using(banco)
            qs_fin = qs_fin.using(banco)
        total_materiais = (
            qs_mov.filter(movm_obra=obra, movm_tipo="SA")
            .annotate(valor_total=F("movm_quan") * F("movm_cuni"))
            .aggregate(total=Sum("valor_total"))
            .get("total")
            or 0
        )
        total_despesas = (
            qs_fin.filter(lfin_obra=obra, lfin_tipo="DE").exclude(lfin_cate="Materiais (Saída)")
            .aggregate(total=Sum("lfin_valo"))
            .get("total")
            or 0
        )
        if banco:
            Obra.objects.using(banco).filter(pk=obra.pk).update(obra_cust=total_materiais + total_despesas)
            obra = Obra.objects.using(banco).get(pk=obra.pk)
        else:
            obra.obra_cust = total_materiais + total_despesas
            obra.save(update_fields=["obra_cust", "obra_alte"])
        return obra

    @staticmethod
    def registrar_movimento_material(banco: str, dados: dict) -> ObraMaterialMovimento:
        with transaction.atomic(using=banco):
            obj = ObraMaterialMovimento.objects.using(banco).create(**dados)
        return obj

    @staticmethod
    def registrar_lancamento_financeiro(banco: str, dados: dict) -> ObraLancamentoFinanceiro:
        with transaction.atomic(using=banco):
            obj = ObraLancamentoFinanceiro.objects.using(banco).create(**dados)
        return obj

    @staticmethod
    def registrar_movimentos_materiais_lote(banco: str, obra: Obra, cabecalho: dict, itens: list[dict], gerar_financeiro: bool, opcoes_financeiro: dict | None = None) -> list[ObraMaterialMovimento]:
        movimentos = []
        if not itens:
            return movimentos
        base_codi = int(cabecalho.get("movm_codi") or 0)
        codigos = [base_codi + i for i in range(len(itens))]
        existentes = (
            ObraMaterialMovimento.objects.using(banco)
            .filter(movm_empr=obra.obra_empr, movm_fili=obra.obra_fili, movm_codi__in=codigos)
            .values_list("movm_codi", flat=True)
        )
        existentes = list(existentes)
        if existentes:
            raise ValueError(f"Código(s) já utilizado(s): {', '.join(str(x) for x in existentes)}")

        movimentar_estoque = bool(cabecalho.get("movimentar_estoque", True))
        usuario_id = cabecalho.get("usuario_id")
        with transaction.atomic(using=banco):
            for idx, item in enumerate(itens):
                dados = {
                    "movm_empr": obra.obra_empr,
                    "movm_fili": obra.obra_fili,
                    "movm_obra_id": obra.id,
                    "movm_codi": base_codi + idx,
                    "movm_data": cabecalho.get("movm_data"),
                    "movm_tipo": cabecalho.get("movm_tipo"),
                    "movm_etap_id": cabecalho.get("movm_etap_id"),
                    "movm_docu": cabecalho.get("movm_docu"),
                    "movm_obse": cabecalho.get("movm_obse"),
                    "movm_prod": item.get("movm_prod"),
                    "movm_desc": item.get("movm_desc"),
                    "movm_unid": item.get("movm_unid"),
                    "movm_quan": item.get("movm_quan"),
                    "movm_cuni": item.get("movm_cuni"),
                }
                mov = ObraMaterialMovimento.objects.using(banco).create(**dados)
                movimentos.append(mov)
                ObrasService.sincronizar_estoque_movimento_material(
                    banco=banco,
                    obra=obra,
                    movimento=mov,
                    movimentar_estoque=movimentar_estoque,
                    usuario_id=usuario_id,
                )
                if gerar_financeiro:
                    ObrasService.gerar_financeiro_do_movimento_material(banco=banco, obra=obra, movimento=mov, opcoes=opcoes_financeiro)
        return movimentos

    @staticmethod
    def gerar_titulo_pagar(banco: str, obra: Obra, fornecedor_id: int, valor, vencimento, historico=None):
        dados = {
            "titu_empr": obra.obra_empr,
            "titu_fili": obra.obra_fili,
            "titu_forn": fornecedor_id,
            "titu_titu": f"OB{obra.obra_codi:07d}",
            "titu_seri": "OB",
            "titu_parc": "001",
            "titu_emis": None,
            "titu_venc": vencimento,
            "titu_valo": valor,
            "titu_hist": historico or f"Obra {obra.obra_codi} - {obra.obra_nome}",
        }
        with transaction.atomic(using=banco):
            return Titulospagar.objects.using(banco).create(**dados)

    @staticmethod
    def gerar_titulo_receber(banco: str, obra: Obra, cliente_id: int, valor, vencimento, historico=None):
        dados = {
            "titu_empr": obra.obra_empr,
            "titu_fili": obra.obra_fili,
            "titu_clie": cliente_id,
            "titu_titu": f"OR{obra.obra_codi:07d}",
            "titu_seri": "OB",
            "titu_parc": "001",
            "titu_emis": None,
            "titu_venc": vencimento,
            "titu_valo": valor,
            "titu_hist": historico or f"Obra {obra.obra_codi} - {obra.obra_nome}",
        }
        with transaction.atomic(using=banco):
            return Titulosreceber.objects.using(banco).create(**dados)

    @staticmethod
    def proximo_codigo_obra(banco: str, empresa: int, filial: int) -> int:
        ultimo = (
            Obra.objects.using(banco)
            .filter(obra_empr=empresa, obra_fili=filial)
            .aggregate(m=Max("obra_codi"))
            .get("m")
            or 0
        )
        return int(ultimo) + 1

    @staticmethod
    def proximo_codigo_financeiro(banco: str, empresa: int, filial: int) -> int:
        ultimo = (
            ObraLancamentoFinanceiro.objects.using(banco)
            .filter(lfin_empr=empresa, lfin_fili=filial)
            .aggregate(m=Max("lfin_codi"))
            .get("m")
            or 0
        )
        return int(ultimo) + 1

    @staticmethod
    def proximo_codigo_etapa(banco: str, empresa: int, filial: int) -> int:
        ultimo = (
            ObraEtapa.objects.using(banco)
            .filter(etap_empr=empresa, etap_fili=filial)
            .aggregate(m=Max("etap_codi"))
            .get("m")
            or 0
        )
        return int(ultimo) + 1

    @staticmethod
    def proximo_codigo_movimento_material(banco: str, empresa: int, filial: int) -> int:
        ultimo = (
            ObraMaterialMovimento.objects.using(banco)
            .filter(movm_empr=empresa, movm_fili=filial)
            .aggregate(m=Max("movm_codi"))
            .get("m")
            or 0
        )
        return int(ultimo) + 1

    @staticmethod
    def gerar_financeiro_do_movimento_material(banco: str, obra: Obra, movimento: ObraMaterialMovimento, opcoes: dict | None = None) -> ObraLancamentoFinanceiro:
        mov_id = getattr(movimento, "id", None)
        if mov_id:
            existente = (
                ObraLancamentoFinanceiro.objects.using(banco)
                .filter(lfin_obra_id=obra.id)
                .filter(lfin_obse__icontains=f"mov_id={mov_id}")
                .order_by("-lfin_codi")
                .first()
            )
            if existente:
                return existente

        quantidade = getattr(movimento, "movm_quan", 0) or 0
        unitario = getattr(movimento, "movm_cuni", 0) or 0
        valor = quantidade * unitario
        tipo_mov = getattr(movimento, "movm_tipo", "") or ""
        categoria = "Materiais (Entrada)" if tipo_mov == "EN" else "Materiais (Saída)"
        desc_prod = (getattr(movimento, "movm_desc", "") or "").strip()
        codi_prod = (getattr(movimento, "movm_prod", "") or "").strip()
        desc = f"{codi_prod} - {desc_prod}".strip(" -")
        desc = desc[:255]
        tipo_fin = "DE"
        parcelas = 1
        primeiro_venc = getattr(movimento, "movm_data", date.today())
        intervalo = 30

        def _to_date(v):
            if not v:
                return None
            if isinstance(v, date) and not isinstance(v, datetime):
                return v
            if isinstance(v, datetime):
                return v.date()
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    return None
                try:
                    return date.fromisoformat(s)
                except Exception:
                    pass
                try:
                    return datetime.strptime(s, "%d/%m/%Y").date()
                except Exception:
                    return None
            return None

        if opcoes:
            tipo_fin = (opcoes.get("tipo") or tipo_fin)[:2]
            try:
                parcelas = max(1, int(opcoes.get("parcelas") or 1))
            except Exception:
                parcelas = 1
            primeiro_venc = _to_date(opcoes.get("primeiro_vencimento")) or primeiro_venc
            try:
                intervalo = max(1, int(opcoes.get("intervalo_dias") or intervalo))
            except Exception:
                intervalo = 30

        if parcelas <= 1:
            dados = {
                "lfin_empr": obra.obra_empr,
                "lfin_fili": obra.obra_fili,
                "lfin_codi": ObrasService.proximo_codigo_financeiro(banco, obra.obra_empr, obra.obra_fili),
                "lfin_obra_id": obra.id,
                "lfin_etap_id": getattr(movimento, "movm_etap_id", None),
                "lfin_tipo": tipo_fin,
                "lfin_cate": categoria,
                "lfin_desc": desc or "Movimento de Materiais",
                "lfin_valo": valor,
                "lfin_dcom": primeiro_venc,
                "lfin_obse": f"Gerado via movimentação de materiais ({tipo_mov}) mov_id={mov_id}",
            }
            with transaction.atomic(using=banco):
                return ObraLancamentoFinanceiro.objects.using(banco).create(**dados)
        else:
            from decimal import Decimal, ROUND_HALF_UP
            total = Decimal(str(valor))
            base = (total / Decimal(parcelas)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            valores = [base for _ in range(parcelas)]
            ajuste = total - sum(valores)
            if ajuste != Decimal("0.00"):
                valores[-1] = (valores[-1] + ajuste).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            primeiro_obj = None
            with transaction.atomic(using=banco):
                for i in range(parcelas):
                    venc = primeiro_venc + timedelta(days=intervalo * i)
                    dados = {
                        "lfin_empr": obra.obra_empr,
                        "lfin_fili": obra.obra_fili,
                        "lfin_codi": ObrasService.proximo_codigo_financeiro(banco, obra.obra_empr, obra.obra_fili),
                        "lfin_obra_id": obra.id,
                        "lfin_etap_id": getattr(movimento, "movm_etap_id", None),
                        "lfin_tipo": tipo_fin,
                        "lfin_cate": categoria,
                        "lfin_desc": (desc or "Movimento de Materiais"),
                        "lfin_valo": valores[i],
                        "lfin_dcom": venc,
                        "lfin_obse": f"Gerado via movimentação de materiais ({tipo_mov}) mov_id={mov_id} parc={i+1}/{parcelas}",
                    }
                    obj = ObraLancamentoFinanceiro.objects.using(banco).create(**dados)
                    if i == 0:
                        primeiro_obj = obj
            return primeiro_obj

    @staticmethod
    def atualizar_status_obra(banco: str, obra_id: int, novo_status: str) -> Obra:
        obra = Obra.objects.using(banco).get(pk=obra_id)
        valido = novo_status in {"PL", "EA", "PA", "CO", "CA"}
        if not valido:
            return obra
        obra.obra_stat = novo_status
        if novo_status == "CO" and not obra.obra_dfim:
            obra.obra_dfim = date.today()
        obra.save(using=banco, update_fields=["obra_stat", "obra_dfim", "obra_alte"])
        return obra
