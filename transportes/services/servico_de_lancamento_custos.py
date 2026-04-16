from decimal import Decimal
from django.db import transaction
from django.db.models import Max, Q
from transportes.models import Custos, Veiculos
from Entidades.models import Entidades


class LancamentoCustosService:

    @staticmethod
    def gerar_sequencial(empresa_id, filial_id, using='default'):
        max_ctrl = Custos.objects.using(using).filter(
            lacu_empr=empresa_id,
            lacu_fili=filial_id,
        ).aggregate(Max('lacu_ctrl'))['lacu_ctrl__max']
        return (max_ctrl or 0) + 1

    @staticmethod
    def get_custo(empresa_id, filial_id, custo_id, using='default'):
        return Custos.objects.using(using).filter(
            lacu_empr=empresa_id,
            lacu_fili=filial_id,
            lacu_ctrl=custo_id,
        ).first()

    @staticmethod
    def validar_dados(data, using='default'):
        empresa_id = data.get("lacu_empr")
        filial_id = data.get("lacu_fili")

        if not empresa_id:
            raise ValueError("Empresa é obrigatória")

        if not filial_id:
            raise ValueError("Filial é obrigatória")

        transportadoras = Entidades.objects.using(using).filter(
            enti_empr=empresa_id,
            enti_tien='T',
        )

        frota_id = data.get("lacu_frot")
        if frota_id and not transportadoras.filter(enti_clie=frota_id).exists():
            raise ValueError("Frota/Transportadora não encontrada")

        veiculo_id = data.get("lacu_veic")
        if frota_id and veiculo_id:
            if not Veiculos.objects.using(using).filter(
                veic_empr=empresa_id,
                veic_tran=frota_id,
                veic_sequ=veiculo_id,
            ).filter(Q(veic_inat=False) | Q(veic_inat__isnull=True)).exists():
                raise ValueError("Veículo não encontrado para a transportadora")

        if data.get("lacu_moto"):
            if not Entidades.objects.using(using).filter(
                enti_empr=empresa_id,
                enti_clie=data.get("lacu_moto")
            ).exists():
                raise ValueError("Funcionário/Motorista não encontrado")

        if data.get("lacu_forn"):
            if not Entidades.objects.using(using).filter(
                enti_empr=empresa_id,
                enti_clie=data.get("lacu_forn")
            ).exists():
                raise ValueError("Fornecedor não encontrado")

        if not data.get("lacu_quan"):
            raise ValueError("Quantidade é obrigatória")

        if not data.get("lacu_unit"):
            raise ValueError("Preço unitário é obrigatório")

        if not data.get("lacu_item"):
            raise ValueError("Item/Insumo é obrigatório")

        if not data.get("lacu_nome_item"):
            raise ValueError("Descrição do item é obrigatória")

    @staticmethod
    def create_custo(data, user_id, using='default'):
        with transaction.atomic(using=using):
            LancamentoCustosService.validar_dados(data, using)

            allowed = {f.name for f in Custos._meta.fields}
            data_to_save = {k: v for k, v in data.items() if k in allowed}

            custo = Custos(**data_to_save)
            custo.lacu_ctrl = LancamentoCustosService.gerar_sequencial(
                custo.lacu_empr,
                custo.lacu_fili,
                using,
            )

            if hasattr(custo, "lacu_usua_nome"):
                custo.lacu_usua_nome = user_id
            if hasattr(custo, "lacu_usua_alte"):
                custo.lacu_usua_alte = user_id

            if custo.lacu_quan and custo.lacu_unit:
                custo.lacu_tota = custo.lacu_quan * custo.lacu_unit

            custo.save(using=using, force_insert=True)
            return custo

    @staticmethod
    def update_custo(custo, data, user_id, using='default'):
        with transaction.atomic(using=using):
            data["lacu_empr"] = int(data.get("lacu_empr") or custo.lacu_empr)
            data["lacu_fili"] = int(data.get("lacu_fili") or custo.lacu_fili)
            LancamentoCustosService.validar_dados(data, using)

            campos_permitidos = {
                "lacu_frot", "lacu_data", "lacu_moto", "lacu_forn",
                "lacu_item", "lacu_nome_item", "lacu_quan", "lacu_unit",
                "lacu_tota", "lacu_obse", "lacu_veic", "lacu_docu", "lacu_nota", "lacu_cupo",
            }

            update_data = {}
            for key, value in data.items():
                if key in campos_permitidos:
                    update_data[key] = value

            if "lacu_usua_alte" in {f.name for f in Custos._meta.fields}:
                update_data["lacu_usua_alte"] = user_id

            nova_quan = update_data.get("lacu_quan", custo.lacu_quan)
            novo_unit = update_data.get("lacu_unit", custo.lacu_unit)
            if nova_quan and novo_unit:
                update_data["lacu_tota"] = Decimal(nova_quan) * Decimal(novo_unit)

            Custos.objects.using(using).filter(
                lacu_empr=data.get("lacu_empr"),
                lacu_fili=data.get("lacu_fili"),
                lacu_ctrl=custo.lacu_ctrl,
            ).update(**update_data)

            return Custos.objects.using(using).filter(
                lacu_empr=data.get("lacu_empr"),
                lacu_fili=data.get("lacu_fili"),
                lacu_ctrl=custo.lacu_ctrl,
            ).first()

    @staticmethod
    def delete_custo(*, custo, user_id, using="default"):
        with transaction.atomic(using=using):
            empresa_id = int(getattr(custo, "lacu_empr", 0) or 0)
            filial_id = int(getattr(custo, "lacu_fili", 0) or 0)

            Custos.objects.using(using).filter(
                lacu_empr=empresa_id,
                lacu_fili=filial_id,
                lacu_ctrl=getattr(custo, "lacu_ctrl", None),
            ).delete()
