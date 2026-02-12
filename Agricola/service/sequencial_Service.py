from django.db import transaction
from ..models import SequencialControle


class SequencialService:

    @staticmethod
    def gerar(*, empresa, filial, tipo, chave_extra=None, using=None):
        with transaction.atomic(using=using):
            qs = SequencialControle.objects.using(using)

            registro, created = (
                qs.select_for_update()
                .get_or_create(
                seq_empr=empresa,
                seq_fili=filial,
                seq_tipo=tipo,
                seq_chave_extra=chave_extra,
                defaults={"seq_atual": 0},
            )
        )

            registro.seq_atual += 1
            registro.save(using=using)

            return registro.seq_atual
