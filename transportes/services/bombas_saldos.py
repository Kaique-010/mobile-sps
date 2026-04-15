from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
from django.db.models.functions import Coalesce

from Produtos.models import Produtos
from transportes.models import Bombas, BombasSaldos


class BombasSaldosService:
    @staticmethod
    def _delta(tipo_movi: int, quantidade: Decimal):
        q = Decimal(quantidade)
        return q if int(tipo_movi) == 1 else q * Decimal("-1")

    @staticmethod
    def calcular_saldo_atual(*, using: str, empresa_id: int, filial_id: int, bomb_bomb: str, bomb_comb: str):
        qs = BombasSaldos.objects.using(using).filter(
            bomb_empr=empresa_id,
            bomb_fili=filial_id,
            bomb_bomb=str(bomb_bomb),
            bomb_comb=str(bomb_comb),
        )
        saldo = qs.aggregate(
            saldo=Coalesce(
                Sum(
                    Case(
                        When(bomb_tipo_movi=1, then=F("bomb_sald")),
                        When(bomb_tipo_movi=2, then=F("bomb_sald") * Decimal("-1")),
                        default=Decimal("0"),
                        output_field=DecimalField(max_digits=15, decimal_places=4),
                    )
                ),
                Decimal("0"),
            )
        )["saldo"]
        return saldo or Decimal("0")

    @staticmethod
    def registrar_movimentacao(
        *,
        using: str,
        empresa_id: int,
        filial_id: int,
        bomb_bomb: str,
        bomb_comb: str,
        tipo_movi: int,
        quantidade: Decimal,
        data,
        usuario_id: int | None,
    ):
        if tipo_movi not in (1, 2):
            raise ValidationError("Tipo de movimentação inválido")
        if quantidade is None or Decimal(quantidade) <= 0:
            raise ValidationError("Quantidade deve ser maior que zero")

        if not Bombas.objects.using(using).filter(bomb_empr=empresa_id, bomb_codi=str(bomb_bomb)).exists():
            raise ValidationError("Bomba não encontrada")

        if not Produtos.objects.using(using).filter(prod_empr=str(empresa_id), prod_codi=str(bomb_comb)).exists():
            raise ValidationError("Combustível não encontrado")

        with transaction.atomic(using=using):
            saldo_atual = BombasSaldosService.calcular_saldo_atual(
                using=using,
                empresa_id=empresa_id,
                filial_id=filial_id,
                bomb_bomb=bomb_bomb,
                bomb_comb=bomb_comb,
            )
            if tipo_movi == 2 and saldo_atual < Decimal(quantidade):
                raise ValidationError("Saldo insuficiente na bomba para esse combustível")

            mov = BombasSaldos.objects.using(using).create(
                bomb_empr=empresa_id,
                bomb_fili=filial_id,
                bomb_bomb=str(bomb_bomb),
                bomb_comb=str(bomb_comb),
                bomb_sald=Decimal(quantidade),
                bomb_tipo_movi=tipo_movi,
                bomb_data=data,
                bomb_usua=usuario_id,
            )

            saldo_depois = saldo_atual + Decimal(quantidade) if tipo_movi == 1 else saldo_atual - Decimal(quantidade)
            return mov, saldo_atual, saldo_depois

    @staticmethod
    def atualizar_movimentacao(
        *,
        using: str,
        empresa_id: int,
        filial_id: int,
        bomb_id: int,
        bomb_bomb: str,
        bomb_comb: str,
        tipo_movi: int,
        quantidade: Decimal,
        data,
        usuario_id: int | None,
    ):
        if tipo_movi not in (1, 2):
            raise ValidationError("Tipo de movimentação inválido")
        if quantidade is None or Decimal(quantidade) <= 0:
            raise ValidationError("Quantidade deve ser maior que zero")

        if not Bombas.objects.using(using).filter(bomb_empr=empresa_id, bomb_codi=str(bomb_bomb)).exists():
            raise ValidationError("Bomba não encontrada")

        if not Produtos.objects.using(using).filter(prod_empr=str(empresa_id), prod_codi=str(bomb_comb)).exists():
            raise ValidationError("Combustível não encontrado")

        with transaction.atomic(using=using):
            mov = BombasSaldos.objects.using(using).select_for_update().get(
                bomb_id=bomb_id,
                bomb_empr=empresa_id,
                bomb_fili=filial_id,
            )
            saldo_atual = BombasSaldosService.calcular_saldo_atual(
                using=using,
                empresa_id=empresa_id,
                filial_id=filial_id,
                bomb_bomb=mov.bomb_bomb,
                bomb_comb=mov.bomb_comb,
            )
            saldo_base = saldo_atual - BombasSaldosService._delta(mov.bomb_tipo_movi, mov.bomb_sald or 0)
            saldo_depois = saldo_base + BombasSaldosService._delta(tipo_movi, quantidade)
            if saldo_depois < 0:
                raise ValidationError("Saldo insuficiente na bomba para esse combustível")

            mov.bomb_bomb = str(bomb_bomb)
            mov.bomb_comb = str(bomb_comb)
            mov.bomb_tipo_movi = int(tipo_movi)
            mov.bomb_sald = Decimal(quantidade)
            mov.bomb_data = data
            mov.bomb_usua = usuario_id
            mov.save(using=using)
            return mov, saldo_base, saldo_depois

    @staticmethod
    def excluir_movimentacao(*, using: str, empresa_id: int, filial_id: int, bomb_id: int):
        with transaction.atomic(using=using):
            mov = BombasSaldos.objects.using(using).select_for_update().get(
                bomb_id=bomb_id,
                bomb_empr=empresa_id,
                bomb_fili=filial_id,
            )
            saldo_atual = BombasSaldosService.calcular_saldo_atual(
                using=using,
                empresa_id=empresa_id,
                filial_id=filial_id,
                bomb_bomb=mov.bomb_bomb,
                bomb_comb=mov.bomb_comb,
            )
            saldo_depois = saldo_atual - BombasSaldosService._delta(mov.bomb_tipo_movi, mov.bomb_sald or 0)
            if saldo_depois < 0:
                raise ValidationError("Operação inválida: saldo ficaria negativo")
            mov.delete(using=using)
            return saldo_atual, saldo_depois
