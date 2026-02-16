from django.db import transaction
from decimal import Decimal
from .models import Adiantamentos
from Entidades.models import Entidades
from Agricola.service.sequencial_Service import SequencialService


class EntidadesServiceNome:
    def get(self, *, empresa, enti_clie, using):
        try:
            entidade = Entidades.objects.using(using).get(
                enti_clie=enti_clie,
                enti_empr=empresa,
            )
            return entidade.enti_nome
        except Entidades.DoesNotExist:
            return None


class AdiantamentosService:
    @staticmethod
    @transaction.atomic
    def criar_adiantamento(*, dados, using):
        empresa = dados.get('adia_empr')
        filial = dados.get('adia_fili')
        serie = dados.get('adia_seri')

        if empresa is None or filial is None or not serie:
            raise ValueError('adia_empr, adia_fili e adia_seri são obrigatórios para gerar o adiantamento')

        numero = SequencialService.gerar(
            empresa=empresa,
            filial=filial,
            tipo='ADIANTAMENTO',
            chave_extra=serie,
            using=using,
        )

        if not dados.get('adia_ctrl'):
            dados['adia_ctrl'] = str(numero).zfill(4)

        if dados.get('adia_valo') is not None and dados.get('adia_sald') is None:
            dados['adia_sald'] = dados['adia_valo']

        adiantamento = Adiantamentos.objects.using(using).create(**dados)
        return adiantamento

    @staticmethod
    def get_adiantamento(*, empresa, entidade, documento, serie, using):
        try:
            return Adiantamentos.objects.using(using).get(
                adia_empr=empresa,
                adia_enti=entidade,
                adia_docu=documento,
                adia_seri=serie,
            )
        except Adiantamentos.DoesNotExist:
            return None

    @staticmethod
    def get_all(using):
        return Adiantamentos.objects.using(using).all()

    @staticmethod
    def update(adiantamento, validated_data, using):
        for key, value in validated_data.items():
            setattr(adiantamento, key, value)
        adiantamento.save(using=using)
        return adiantamento

    @staticmethod
    def delete(adiantamento, using):
        adiantamento.delete(using=using)

    @staticmethod
    @transaction.atomic
    def usar_adiantamento(*, adiantamento, valor, using, origem=None, referencia=None):
        if valor is None:
            raise ValueError('Valor é obrigatório')
        valor = Decimal(valor)

        if valor <= 0:
            raise ValueError('Valor deve ser positivo para usar adiantamento')

        adiantamento.adia_valo = adiantamento.adia_valo or Decimal('0')
        adiantamento.adia_sald = adiantamento.adia_sald if adiantamento.adia_sald is not None else adiantamento.adia_valo
        adiantamento.adia_util = adiantamento.adia_util or Decimal('0')

        if valor > adiantamento.adia_sald:
            raise ValueError('Saldo insuficiente no adiantamento')

        novo_util = adiantamento.adia_util + valor
        novo_sald = adiantamento.adia_sald - valor

        Adiantamentos.objects.using(using).filter(
            adia_empr=adiantamento.adia_empr,
            adia_fili=adiantamento.adia_fili,
            adia_enti=adiantamento.adia_enti,
            adia_docu=adiantamento.adia_docu,
            adia_seri=adiantamento.adia_seri,
        ).update(
            adia_util=novo_util,
            adia_sald=novo_sald,
        )

        adiantamento.adia_util = novo_util
        adiantamento.adia_sald = novo_sald
        return adiantamento

    @staticmethod
    @transaction.atomic
    def estornar_adiantamento(*, adiantamento, valor, using):
        if valor is None:
            raise ValueError('Valor é obrigatório para estorno')
        valor = Decimal(valor)

        if valor <= 0:
            raise ValueError('Valor deve ser positivo para estorno de adiantamento')

        adiantamento.adia_valo = adiantamento.adia_valo or Decimal('0')
        adiantamento.adia_sald = adiantamento.adia_sald if adiantamento.adia_sald is not None else adiantamento.adia_valo
        adiantamento.adia_util = adiantamento.adia_util or Decimal('0')

        if valor > adiantamento.adia_util:
            raise ValueError('Valor de estorno maior que o valor já utilizado do adiantamento')

        novo_util = adiantamento.adia_util - valor
        novo_sald = adiantamento.adia_sald + valor

        Adiantamentos.objects.using(using).filter(
            adia_empr=adiantamento.adia_empr,
            adia_fili=adiantamento.adia_fili,
            adia_enti=adiantamento.adia_enti,
            adia_docu=adiantamento.adia_docu,
            adia_seri=adiantamento.adia_seri,
        ).update(
            adia_util=novo_util,
            adia_sald=novo_sald,
        )

        adiantamento.adia_util = novo_util
        adiantamento.adia_sald = novo_sald
        return adiantamento

    @staticmethod
    @transaction.atomic
    def estornar_adiantamento_by_context(*, empresa, filial, entidade, tipo, valor, using):
        if valor is None:
            raise ValueError('Valor é obrigatório para estorno')
        valor = Decimal(valor)

        if valor <= 0:
            raise ValueError('Valor deve ser positivo para estorno de adiantamento')

        qs = Adiantamentos.objects.using(using).filter(
            adia_empr=empresa,
            adia_fili=filial,
            adia_enti=entidade,
        )
        if tipo:
            qs = qs.filter(adia_tipo=tipo)

        adiantamento = qs.order_by('-adia_docu', '-adia_seri').first()
        if not adiantamento:
            raise ValueError('Nenhum adiantamento encontrado para estorno')

        return AdiantamentosService.estornar_adiantamento(
            adiantamento=adiantamento,
            valor=valor,
            using=using,
        )

    @staticmethod
    def get_disponivel(*, empresa, filial, entidade, tipo, using):
        base = Adiantamentos.objects.using(using).filter(
            adia_empr=empresa,
            adia_fili=filial,
            adia_enti=entidade,
        )
        if tipo:
            qs = base.filter(adia_tipo=tipo, adia_sald__gt=0)
            candidato = qs.order_by('adia_docu', 'adia_seri').first()
            if candidato:
                return candidato
        return base.filter(adia_sald__gt=0).order_by('adia_docu', 'adia_seri').first()

    @staticmethod
    @transaction.atomic
    def usar_adiantamento_by_context(*, empresa, filial, entidade, tipo, valor, using, referencia=None):
        adiantamento = AdiantamentosService.get_disponivel(
            empresa=empresa,
            filial=filial,
            entidade=entidade,
            tipo=tipo,
            using=using,
        )
        if not adiantamento:
            raise ValueError('Nenhum adiantamento com saldo disponível encontrado')

        return AdiantamentosService.usar_adiantamento(
            adiantamento=adiantamento,
            valor=valor,
            using=using,
            origem=tipo,
            referencia=referencia,
        )

