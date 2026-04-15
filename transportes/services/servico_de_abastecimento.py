from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from transportes.models import Abastecusto, Bombas
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
    def registrar_consumo_combustivel(
        *,
        using: str,
        empresa_id: int,
        filial_id: int,
        bomb_bomb: str,
        bomb_comb: str,
        quantidade,
        data,
        usuario_id: int | None,
    ):
        try:
            return BombasSaldosService.registrar_movimentacao(
                using=using,
                empresa_id=int(empresa_id),
                filial_id=int(filial_id),
                bomb_bomb=str(bomb_bomb),
                bomb_comb=str(bomb_comb),
                tipo_movi=2,
                quantidade=Decimal(quantidade),
                data=data,
                usuario_id=usuario_id,
            )
        except ValidationError as exc:
            msgs = getattr(exc, "messages", None)
            raise ValueError("; ".join(msgs) if msgs else str(exc))

    @staticmethod
    def registrar_estorno_combustivel(
        *,
        using: str,
        empresa_id: int,
        filial_id: int,
        bomb_bomb: str,
        bomb_comb: str,
        quantidade,
        data,
        usuario_id: int | None,
    ):
        try:
            return BombasSaldosService.registrar_movimentacao(
                using=using,
                empresa_id=int(empresa_id),
                filial_id=int(filial_id),
                bomb_bomb=str(bomb_bomb),
                bomb_comb=str(bomb_comb),
                tipo_movi=1,
                quantidade=Decimal(quantidade),
                data=data,
                usuario_id=usuario_id,
            )
        except ValidationError as exc:
            msgs = getattr(exc, "messages", None)
            raise ValueError("; ".join(msgs) if msgs else str(exc))

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

        if not data.get("abas_bomb"):
            raise ValueError("Bomba é obrigatória")

        if not Bombas.objects.using(using).filter(
            bomb_empr=empresa_id,
            bomb_codi=str(data.get("abas_bomb")),
        ).exists():
            raise ValueError("Bomba não encontrada")

        # ⛽ Combustível (Produto)
        if not data.get("abas_comb"):
            raise ValueError("Combustível é obrigatório")
        if not Produtos.objects.using(using).filter(
            prod_empr=str(empresa_id),
            prod_codi=str(data.get("abas_comb"))
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

            AbastecimentoService.registrar_consumo_combustivel(
                using=using,
                empresa_id=abastecimento.abas_empr,
                filial_id=abastecimento.abas_fili,
                bomb_bomb=abastecimento.abas_bomb,
                bomb_comb=abastecimento.abas_comb,
                quantidade=abastecimento.abas_quan,
                data=abastecimento.abas_data,
                usuario_id=user_id,
            )

            abastecimento.save(using=using, force_insert=True)
            return abastecimento

    @staticmethod
    def update_abastecimento(abastecimento, data, user_id, using='default'):
        with transaction.atomic(using=using):
            AbastecimentoService.validar_dados(data, using)

            empresa_id = int(data.get("abas_empr") or abastecimento.abas_empr)
            filial_id = int(data.get("abas_fili") or abastecimento.abas_fili)

            old_bomb = str(getattr(abastecimento, "abas_bomb", "") or "")
            old_comb = str(getattr(abastecimento, "abas_comb", "") or "")
            old_quan = Decimal(getattr(abastecimento, "abas_quan", None) or 0)

            new_bomb = str(data.get("abas_bomb") or old_bomb)
            new_comb = str(data.get("abas_comb") or old_comb)
            new_quan = Decimal(data.get("abas_quan") or old_quan or 0)
            mov_data = data.get("abas_data") or getattr(abastecimento, "abas_data", None)

            if old_bomb and old_comb and old_quan > 0:
                if old_bomb == new_bomb and old_comb == new_comb:
                    delta = new_quan - old_quan
                    if delta > 0:
                        AbastecimentoService.registrar_consumo_combustivel(
                            using=using,
                            empresa_id=empresa_id,
                            filial_id=filial_id,
                            bomb_bomb=new_bomb,
                            bomb_comb=new_comb,
                            quantidade=delta,
                            data=mov_data,
                            usuario_id=user_id,
                        )
                    elif delta < 0:
                        AbastecimentoService.registrar_estorno_combustivel(
                            using=using,
                            empresa_id=empresa_id,
                            filial_id=filial_id,
                            bomb_bomb=new_bomb,
                            bomb_comb=new_comb,
                            quantidade=abs(delta),
                            data=mov_data,
                            usuario_id=user_id,
                        )
                else:
                    AbastecimentoService.registrar_estorno_combustivel(
                        using=using,
                        empresa_id=empresa_id,
                        filial_id=filial_id,
                        bomb_bomb=old_bomb,
                        bomb_comb=old_comb,
                        quantidade=old_quan,
                        data=mov_data,
                        usuario_id=user_id,
                    )

                    AbastecimentoService.registrar_consumo_combustivel(
                        using=using,
                        empresa_id=empresa_id,
                        filial_id=filial_id,
                        bomb_bomb=new_bomb,
                        bomb_comb=new_comb,
                        quantidade=new_quan,
                        data=mov_data,
                        usuario_id=user_id,
                    )

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

    @staticmethod
    def delete_abastecimento(*, abastecimento, user_id, using="default"):
        with transaction.atomic(using=using):
            empresa_id = int(getattr(abastecimento, "abas_empr", 0) or 0)
            filial_id = int(getattr(abastecimento, "abas_fili", 0) or 0)
            bomb_bomb = str(getattr(abastecimento, "abas_bomb", "") or "")
            bomb_comb = str(getattr(abastecimento, "abas_comb", "") or "")
            quantidade = Decimal(getattr(abastecimento, "abas_quan", None) or 0)
            mov_data = getattr(abastecimento, "abas_data", None)

            if bomb_bomb and bomb_comb and quantidade > 0 and empresa_id and filial_id:
                AbastecimentoService.registrar_estorno_combustivel(
                    using=using,
                    empresa_id=empresa_id,
                    filial_id=filial_id,
                    bomb_bomb=bomb_bomb,
                    bomb_comb=bomb_comb,
                    quantidade=quantidade,
                    data=mov_data,
                    usuario_id=user_id,
                )

            Abastecusto.objects.using(using).filter(
                abas_empr=empresa_id,
                abas_fili=filial_id,
                abas_ctrl=getattr(abastecimento, "abas_ctrl", None),
            ).delete()
