from django.core.exceptions import ValidationError
from django.db import transaction

from transportes.models import Bombas



class BombasService:
    @staticmethod
    def gerar_sequencial(*, empresa_id: int, using: str):
        qs = (
            Bombas.objects.using(using)
            .filter(bomb_empr=empresa_id)
            .values_list("bomb_codi", flat=True)
        )
        max_num = 0
        for c in qs:
            if c in (None, ""):
                continue
            s = str(c).strip()
            if not s.isdigit():
                continue
            n = int(s)
            if n > max_num:
                max_num = n

        proximo = max_num + 1
        if proximo > 999999:
            raise ValidationError("Número de bomba muito alto")
        return proximo

    @staticmethod
    def criar(*, empresa_id: int, form, using: str):
        with transaction.atomic(using=using):
            sequencial = BombasService.gerar_sequencial(empresa_id=empresa_id, using=using)
            obj = form.save(commit=False)
            obj.bomb_empr = empresa_id
            obj.bomb_codi = str(sequencial)
            obj.save(using=using, force_insert=True)
            return obj

    @staticmethod
    def editar(*, empresa_id: int, bomb_codi: str, form, using: str):
        with transaction.atomic(using=using):
            pk_fields = ["bomb_empr", "bomb_codi"]
            update_data = {}
            for field_name, value in form.cleaned_data.items():
                if field_name not in pk_fields:
                    update_data[field_name] = value

            Bombas.objects.using(using).filter(
                bomb_empr=empresa_id,
                bomb_codi=bomb_codi,
            ).update(**update_data)

            return Bombas.objects.using(using).filter(
                bomb_empr=empresa_id,
                bomb_codi=bomb_codi,
            ).first()

    @staticmethod
    def excluir(*, empresa_id: int, bomb_codi: str, using: str):
        with transaction.atomic(using=using):
            Bombas.objects.using(using).filter(
                bomb_empr=empresa_id,
                bomb_codi=bomb_codi,
            ).delete()
