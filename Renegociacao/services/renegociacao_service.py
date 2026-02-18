from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from ..models import Renegociado
from contas_a_receber.models import Titulosreceber
from core.utils import get_db_from_slug
from ..calculadora import RenegociacaoCalculadora
from ..gerador_parcelas import ParcelasGenerator
from datetime import datetime, date


class RenegociacaoService:

    @staticmethod
    def listar_titulos_por_cliente(
        *,
        slug: str,
        empresa_id: int,
        filial_id: int,
        cliente_id: int,
    ):
        banco = get_db_from_slug(slug)
        qs = (Titulosreceber.objects
              .using(banco)
              .filter(
                  titu_empr=empresa_id,
                  titu_fili=filial_id,
                  titu_clie=cliente_id,
                  titu_aber="A",
              )
              .only("titu_titu", "titu_seri", "titu_parc", "titu_venc", "titu_valo", "titu_aber")
              .order_by("titu_venc", "titu_titu", "titu_parc"))
        return qs

    @staticmethod
    def criar_renegociacao(
        *,
        slug: str,
        empresa_id: int,
        filial_id: int,
        titulos_ids: list,
        juros: Decimal = Decimal("0"),
        multa: Decimal = Decimal("0"),
        desconto: Decimal = Decimal("0"),
        parcelas: int,
        usuario_id: int,
        vencimento_base: date | None = None,
        regra_parc: str | None = None,
    ):
        banco = get_db_from_slug(slug)
        with transaction.atomic(using=banco):
            titulos = (Titulosreceber.objects
                       .using(banco)
                       .select_for_update()
                       .filter(titu_titu__in=titulos_ids, titu_aber="A"))

            if not titulos.exists():
                raise Exception("Nenhum título elegível para renegociação.")

            # Garantir que todos do mesmo cliente
            clientes = set(t.titu_clie for t in titulos)
            if len(clientes) != 1:
                raise Exception("Selecione títulos de um único cliente.")
            cliente_id = next(iter(clientes))

            docs = sorted({str(t.titu_titu) for t in titulos if getattr(t, "titu_titu", None)})
            rene_titu_val = ",".join(docs) if docs else None

            valor_consolidado = sum(Decimal(str(t.titu_valo or 0)) for t in titulos)
            valor_final = Decimal(str(valor_consolidado)) + Decimal(str(juros)) + Decimal(str(multa)) - Decimal(str(desconto))

            # Renegociação pai (recursiva) caso algum título já seja de renegociação
            rene_pai = None
            for t in titulos:
                if (t.titu_tipo or "").lower().startswith("renegoc") and getattr(t, "titu_ctrl", None):
                    rene_pai = Renegociado.objects.using(banco).filter(rene_id=t.titu_ctrl).first()
                    if rene_pai:
                        break

            perc_juro = (Decimal("0") if valor_consolidado == 0 else (Decimal(str(juros)) / Decimal(str(valor_consolidado)) * 100))
            perc_mult = (Decimal("0") if valor_consolidado == 0 else (Decimal(str(multa)) / Decimal(str(valor_consolidado)) * 100))

            renegociacao = Renegociado.objects.using(banco).create(
                rene_empr=empresa_id,
                rene_fili=filial_id,
                rene_clie=cliente_id,
                rene_titu=rene_titu_val,
                rene_data=timezone.now().date(),
                rene_usua=usuario_id,
                rene_valo=valor_consolidado,
                rene_valo_juro=juros,
                rene_perc_juro=perc_juro,
                rene_valo_mult=multa,
                rene_perc_mult=perc_mult,
                rene_desc=desconto,
                rene_vlfn=valor_final,
                rene_parc=str(parcelas).zfill(3),
                rene_pai=rene_pai,
            )

            # Atualiza títulos originais
            (Titulosreceber.objects
                .using(banco)
                .filter(titu_titu__in=titulos_ids, titu_aber="A")
                .update(titu_tipo="Renegoc", titu_aber="R", titu_ctrl=renegociacao.rene_id))

            # Gera novas parcelas com arredondamento profissional
            valores = RenegociacaoCalculadora.calcular_parcelas(
                slug=slug,
                valor_final=valor_final,
                parcelas=parcelas,
            )

            base_venc = None
            if isinstance(vencimento_base, date):
                base_venc = vencimento_base
            elif isinstance(vencimento_base, str) and vencimento_base.strip():
                try:
                    base_venc = datetime.strptime(vencimento_base.strip(), "%Y-%m-%d").date()
                except Exception:
                    base_venc = None
            if base_venc is None:
                try:
                    vencs = [t.titu_venc for t in titulos if t.titu_venc]
                    base_venc = max(vencs) if vencs else None
                except Exception:
                    base_venc = None

            offs = None
            if regra_parc:
                s = regra_parc.replace(" ", "").replace("+", ",")
                partes = [p for p in s.split(",") if p]
                try:
                    offs = [int(x) for x in partes]
                except Exception:
                    offs = None
            ParcelasGenerator.gerar(
                slug=slug,
                empresa_id=empresa_id,
                filial_id=filial_id,
                cliente_id=cliente_id,
                renegociacao_id=renegociacao.rene_id,
                valores=valores,
                serie=renegociacao.rene_seri or "REN",
                vencimento_base=base_venc,
                offsets=offs,
            )
            return renegociacao
    
    
    @staticmethod
    def status_renegociacao(
        *,
        slug: str,
        renegociacao_id: int,
    ):
        banco = get_db_from_slug(slug)
        renegociacao = Renegociado.objects.using(banco).filter(rene_id=renegociacao_id).first()
        if not renegociacao:
            raise Exception("Renegociação não encontrada.")
        return renegociacao
    
    @staticmethod
    def listar_renegociacoes(
        *,
        slug: str,
        empresa_id: int,
        filial_id: int,
    ):
        banco = get_db_from_slug(slug)
        renegociacoes = Renegociado.objects.using(banco).filter(
            rene_empr=empresa_id,
            rene_fili=filial_id,
        )
        return renegociacoes
    
    @staticmethod
    def quebrar_acordo(
        *,
        slug: str,
        renegociacao_id: int,
        observacoes: str,
        usuario_id: int,
    ):
        banco = get_db_from_slug(slug)
        with transaction.atomic(using=banco):
            renegociacao = (Renegociado.objects
                            .using(banco)
                            .select_for_update()
                            .get(pk=renegociacao_id))

            if renegociacao.rene_stat != "A":
                raise Exception("Renegociação não está ativa.")

            renegociacao.rene_stat = "Q"
            renegociacao.rene_obse = observacoes
            if usuario_id:
                renegociacao.rene_usua = usuario_id
            renegociacao.save(using=banco)

            # Cancela títulos abertos gerados pela renegociação
            (Titulosreceber.objects
                .using(banco)
                .filter(titu_ctrl=renegociacao.rene_id, titu_aber="A")
                .update(titu_aber="X"))
