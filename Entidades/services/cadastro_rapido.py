# servicos.py
from django.core.exceptions import ValidationError  
from ..models import Entidades
from ..utils import buscar_endereco_por_cep, proxima_entidade


class EntidadeCadastroRapido:

    @staticmethod
    def cadastrar_rapido(
        *,
        data: dict,
        empresa_id: int,
        filial_id: int,
        banco: str,
        cep_fallback: str | None = None,
        cpf: str | None = None
    ):
        cep = data["enti_cep"]
        endereco = buscar_endereco_por_cep(cep)
        cpf = data.get("enti_cpf")

        if not endereco and cep_fallback:
            endereco = buscar_endereco_por_cep(cep_fallback)
            cep = cep_fallback

        if not endereco:
            raise ValidationError("CEP inválido ou não encontrado")
    
        
        if not cpf:
            raise ValidationError("CPF inválido ou não fornecido")
        
        
        proximo_clie = proxima_entidade(empresa_id, filial_id, banco)

        return Entidades.objects.using(banco).create(
            enti_nome=data["enti_nome"],
            enti_fant=data["enti_nome"],
            enti_clie=proximo_clie,
            enti_cep=cep,
            enti_cpf=data["enti_cpf"],
            enti_tipo_enti="AM",
            enti_empr=empresa_id,
        )
        
