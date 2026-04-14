from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Entidades
from transportes.models import MotoristasCadastros
from ..utils import buscar_endereco_por_cep, proxima_entidade, gerar_cpf_fake


class EntidadeMotoristaServico:

    @staticmethod
    @transaction.atomic
    def cadastrar_motorista(
        *,
        data: dict,
        empresa_id: int,
        filial_id: int,
        banco: str,
        cep_fallback: str | None = None
    ):
        cep = data["enti_cep"]
        endereco = buscar_endereco_por_cep(cep)

        if not endereco and cep_fallback:
            endereco = buscar_endereco_por_cep(cep_fallback)
            cep = cep_fallback

        if not endereco:
            raise ValidationError("CEP inválido ou não encontrado")

        proximo_motorista = proxima_entidade(empresa_id, filial_id, banco)

        entidade = Entidades.objects.using(banco).create(
            enti_nome=data["enti_nome"],
            enti_fant=data.get("enti_fant") or data["enti_nome"],
            enti_clie=proximo_motorista,
            enti_cep=cep,
            enti_cpf=data.get("enti_cpf") or gerar_cpf_fake(),
            enti_tipo_enti="M",
            enti_empr=empresa_id,
            enti_fili=filial_id,
        )

        motorista, _ = MotoristasCadastros.objects.using(banco).update_or_create(
            empresa=empresa_id,
            filial=filial_id,
            entidade=entidade.enti_clie,
            defaults={
                "status": "ATV",
            }
        )

        return {
            "entidade": entidade,
            "motorista": motorista,
        }
