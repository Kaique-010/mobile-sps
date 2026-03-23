from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.utils import get_db_from_slug
from Entradas_Estoque.models import EntradaEstoque
from Saidas_Estoque.models import SaidasEstoque
from Produtos.models import ProdutosDetalhados

from ..models import FormulaItem, FormulaProduto, OrdemProducao


class EstoqueService:

    @staticmethod
    def _next_entrada_seq(db: str) -> int:
        max_seq = EntradaEstoque.objects.using(db).aggregate(max_sequ=Max("entr_sequ")).get("max_sequ") or 0
        return int(max_seq) + 1

    @staticmethod
    def _next_saida_seq(db: str) -> int:
        max_seq = SaidasEstoque.objects.using(db).aggregate(max_sequ=Max("said_sequ")).get("max_sequ") or 0
        return int(max_seq) + 1

    @staticmethod
    def _produto_codigo(produto) -> str:
        if hasattr(produto, "prod_codi"):
            return str(produto.prod_codi)
        if hasattr(produto, "pk"):
            return str(produto.pk)
        return str(produto)

    @staticmethod
    def _custo_unitario(produto_codigo: str, empr: int, fili: int, db: str) -> Decimal:
        row = (
            ProdutosDetalhados.objects.using(db)
            .filter(codigo=str(produto_codigo), empresa=str(empr), filial=str(fili))
            .values("custo")
            .first()
        )
        custo = row.get("custo") if row else None
        try:
            return Decimal(str(custo or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def saida(
        produto,
        quantidade: Decimal,
        empr: int,
        fili: int,
        db: str,
        usuario_id: int,
        lote: str | None = None,
    ) -> Decimal:
        codigo = EstoqueService._produto_codigo(produto)
        qtd = Decimal(str(quantidade or 0))
        custo_unit = EstoqueService._custo_unitario(codigo, empr, fili, db)
        total = (custo_unit * qtd).quantize(Decimal("0.01"))
        SaidasEstoque.objects.using(db).create(
            said_sequ=EstoqueService._next_saida_seq(db),
            said_empr=int(empr),
            said_fili=int(fili),
            said_prod=str(codigo),
            said_enti=str(usuario_id),
            said_data=timezone.now().date(),
            said_quan=qtd.quantize(Decimal("0.01")),
            said_tota=total,
            said_obse=f"Ordem Produção{(' Lote ' + str(lote)) if lote else ''}",
            said_usua=int(usuario_id),
            said_lote_vend=None,
        )
        return total

    @staticmethod
    def entrada(
        produto,
        quantidade: Decimal,
        custo_unitario: Decimal,
        empr: int,
        fili: int,
        db: str,
        usuario_id: int,
        lote: str | None = None,
    ) -> int:
        codigo = EstoqueService._produto_codigo(produto)
        qtd = Decimal(str(quantidade or 0))
        unit = Decimal(str(custo_unitario or 0))
        total = (unit * qtd).quantize(Decimal("0.01"))
        obj = EntradaEstoque.objects.using(db).create(
            entr_sequ=EstoqueService._next_entrada_seq(db),
            entr_empr=int(empr),
            entr_fili=int(fili),
            entr_prod=str(codigo),
            entr_enti=str(usuario_id),
            entr_data=timezone.now().date(),
            entr_unit=str(unit.quantize(Decimal("0.01"))),
            entr_quan=qtd.quantize(Decimal("0.01")),
            entr_tota=total,
            entr_obse=f"Ordem Produção{(' Lote ' + str(lote)) if lote else ''}",
            entr_usua=int(usuario_id),
            entr_lote_vend=None,
        )
        return int(obj.entr_sequ)


class ProducaoService:

    @staticmethod
    def executar(op: OrdemProducao, db_slug: str, usuario_id: int):
        db = get_db_from_slug(db_slug)

        with transaction.atomic(using=db):
            if op.op_status != "A":
                raise Exception("Ordem já executada")

            formula = FormulaProduto.objects.using(db).get(
                form_empr=op.op_empr,
                form_fili=op.op_fili,
                form_prod=op.op_prod,
                form_vers=op.op_vers,
                form_ativ=True,
            )

            insumos = FormulaItem.objects.using(db).filter(form_form=formula)

            custo_total = Decimal("0")

            for item in insumos:
                perda = item.form_perd_perc or Decimal("0")

                qtd = item.form_qtde * op.op_quan
                qtd *= (1 + perda / 100)

                if getattr(item, "form_baixa_estoque", True):
                    custo = EstoqueService.saida(
                        produto=item.form_insu,
                        quantidade=qtd,
                        empr=op.op_empr,
                        fili=op.op_fili,
                        db=db,
                        usuario_id=usuario_id,
                        lote=op.op_lote,
                    )
                    custo_total += custo
                else:
                    codigo = EstoqueService._produto_codigo(item.form_insu)
                    custo_unit = EstoqueService._custo_unitario(codigo, op.op_empr, op.op_fili, db)
                    total = (custo_unit * Decimal(str(qtd or 0))).quantize(Decimal("0.01"))
                    custo_total += total

            qtd_prod = Decimal(str(op.op_quan or 0))
            if qtd_prod > 0:
                custo_unit_prod = (custo_total / qtd_prod).quantize(Decimal("0.01"))
                EstoqueService.entrada(
                    produto=formula.form_prod,
                    quantidade=qtd_prod,
                    custo_unitario=custo_unit_prod,
                    empr=op.op_empr,
                    fili=op.op_fili,
                    db=db,
                    usuario_id=usuario_id,
                    lote=op.op_lote,
                )

            op.op_status = "F"
            op.op_data_hora = timezone.now()
            op.save(using=db)
