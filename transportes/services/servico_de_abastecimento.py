from django.db import transaction
from django.db.models import Max, Q
from transportes.models import Abastecusto
from Entidades.models import Entidades
from ..models import Veiculos
from Produtos.models import Produtos
from transportes.services.bombas_saldos import BombasSaldosService


class AbastecimentoService:
    @staticmethod
    def get_saldo_bomba_combustivel(*, using: str, empresa_id: int, filial_id: int, bomb_bomb: str, bomb_comb: str):
        return BombasSaldosService.calcular_saldo_atual(
            using=using,
            empresa_id=int(empresa_id),
            filial_id=int(filial_id),
            bomb_bomb=str(bomb_bomb),
            bomb_comb=str(bomb_comb),
        )

    @staticmethod
    def gerar_sequencial(empresa_id, filial_id, using='default'):
        max_ctrl = Abastecusto.objects.using(using).filter(
            abas_empr=empresa_id,
            abas_fili=filial_id,
        ).aggregate(Max('abas_ctrl'))['abas_ctrl__max']

        return (max_ctrl or 0) + 1

    @staticmethod
    def get_abastecimento(empresa_id, filial_id, abastecimento_id, using='default'):
        return Abastecusto.objects.using(using).filter(
            abas_empr=empresa_id,
            abas_fili=filial_id,
            abas_ctrl=abastecimento_id,
        ).first()

    @staticmethod
    def validar_dados(data, using='default'):
        empresa_id = data.get("abas_empr")
        filial_id = data.get("abas_fili")

        if not empresa_id:
            raise ValueError("Empresa é obrigatória")

        if not filial_id:
            raise ValueError("Filial é obrigatória")

        transportadoras = Entidades.objects.using(using).filter(
            enti_empr=empresa_id,
            enti_tien='T',
        )

        frota_id = data.get("abas_frot")

        if frota_id:
            if not transportadoras.filter(
                enti_clie=frota_id
            ).exists():
                raise ValueError("Frota/Transportadora não encontrada")
            veiculo_sequ = data.get("abas_veic_sequ")
            placa = data.get("abas_plac")
            if veiculo_sequ or placa:
                veiculos = Veiculos.objects.using(using).filter(
                    veic_empr=empresa_id,
                    veic_tran=frota_id,
                ).filter(
                    Q(veic_inat=False) | Q(veic_inat__isnull=True)
                )
                veiculo = None

                if veiculo_sequ:
                    veiculo = veiculos.filter(
                        veic_sequ=veiculo_sequ
                    ).first()

                    if not veiculo:
                        raise ValueError("Veículo não encontrado para a transportadora")

                elif placa:
                    veiculo = veiculos.filter(
                        veic_plac=placa
                    ).first()

                    if not veiculo:
                        raise ValueError("Placa não encontrada para a transportadora")
                if veiculo_sequ and placa:
                    if veiculo.veic_plac != placa:
                        raise ValueError("Veículo e placa não conferem")

                data["abas_veic_sequ"] = veiculo.veic_sequ
                data["abas_plac"] = veiculo.veic_plac

        if data.get("abas_func"):
            if not Entidades.objects.using(using).filter(
                enti_empr=empresa_id,
                enti_clie=data.get("abas_func")
            ).exists():
                raise ValueError("Funcionário não encontrado")
        
        if data.get("abas_enti"):
            if not Entidades.objects.using(using).filter(
                enti_empr=empresa_id,
                enti_clie=data.get("abas_enti")
            ).exists():
                raise ValueError("Fornecedor não encontrado")

        # ⛽ Combustível (Produto)
        if data.get("abas_comb"):
            if not Produtos.objects.using(using).filter(
                prod_empr=empresa_id,
                prod_codi=data.get("abas_comb")
            ).exists():
                raise ValueError("Combustível não encontrado")

        # 📊 Regras básicas
        if not data.get("abas_quan"):
            raise ValueError("Quantidade é obrigatória")

        if not data.get("abas_unit"):
            raise ValueError("Preço unitário é obrigatório")

    @staticmethod
    def create_abastecimento(data, user_id, using='default'):
        with transaction.atomic(using=using):
            # 🔥 valida e normaliza
            AbastecimentoService.validar_dados(data, using)

            allowed = {f.name for f in Abastecusto._meta.fields}
            data_to_save = {k: v for k, v in data.items() if k in allowed}

            abastecimento = Abastecusto(**data_to_save)
            abastecimento.abas_ctrl = AbastecimentoService.gerar_sequencial(
                abastecimento.abas_empr,
                abastecimento.abas_fili,
                using,
            )

            abastecimento.abas_usua_nome = user_id
            abastecimento.abas_usua_alte = user_id

            if abastecimento.abas_quan and abastecimento.abas_unit:
                abastecimento.abas_tota = (
                    abastecimento.abas_quan * abastecimento.abas_unit
                )

            abastecimento.save(using=using, force_insert=True)
            return abastecimento

    @staticmethod
    def update_abastecimento(abastecimento, data, user_id, using='default'):
        with transaction.atomic(using=using):
            AbastecimentoService.validar_dados(data, using)

            campos_permitidos = {
                "abas_frot", "abas_data", "abas_func", "abas_enti",
                "abas_bomb", "abas_comb", "abas_quan", "abas_unit",
                "abas_hokm", "abas_hokm_ante", "abas_obse", "abas_veic_sequ", "abas_plac",
            }

            update_data = {}
            for key, value in data.items():
                if key in campos_permitidos:
                    update_data[key] = value

            update_data["abas_usua_alte"] = user_id
            if update_data.get("abas_quan") and update_data.get("abas_unit"):
                update_data["abas_tota"] = update_data["abas_quan"] * update_data["abas_unit"]

            Abastecusto.objects.using(using).filter(
                abas_empr=data.get("abas_empr"),
                abas_fili=data.get("abas_fili"),
                abas_ctrl=abastecimento.abas_ctrl,
            ).update(**update_data)

            return Abastecusto.objects.using(using).filter(
                abas_empr=data.get("abas_empr"),
                abas_fili=data.get("abas_fili"),
                abas_ctrl=abastecimento.abas_ctrl,
            ).first()
