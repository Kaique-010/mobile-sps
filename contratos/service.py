from django.db.models import Max
from .models import Contratosvendas
from .validators import validate_schema
from .schemas import CONTRATO_CREATE_SCHEMA
from core.utils import get_licenca_db_config    



class ContratoService:
    
    @staticmethod
    def get_contrato(cont_cont, context):
        banco = get_licenca_db_config(context["request"])
        empresa_id = context["empresa_id"]
        filial_id = context["filial_id"]
        try:
            return Contratosvendas.objects.using(banco).get(
                cont_cont=cont_cont,
                cont_empr=empresa_id,
                cont_fili=filial_id
            )
        except Contratosvendas.DoesNotExist:
            raise Exception("Contrato não encontrado.")
    
    @staticmethod
    def create_contrato(data, context):
        banco = get_licenca_db_config(context["request"])   
        empresa_id = context["empresa_id"]
        filial_id = context["filial_id"]
        
        #validação do contrato com o service no schema
        validate_schema(data, CONTRATO_CREATE_SCHEMA)
        
        data["cont_empr"] = empresa_id
        data["cont_fili"] = filial_id

        ultimo_contrato = Contratosvendas.objects.using(banco).filter(
            cont_empr=empresa_id,
            cont_fili=filial_id
        ).aggregate(Max("cont_cont"))["cont_cont__max"]
        if ultimo_contrato is None:
            ultimo_contrato = 0
        return Contratosvendas.objects.using(banco).create(
            cont_cont=ultimo_contrato + 1,
            **data
        )
        
     
     
    @staticmethod
    def update_contrato(cont_cont, data, context):
        banco = get_licenca_db_config(context["request"])
        empresa_id = context["empresa_id"]
        filial_id = context["filial_id"]
        contrato = Contratosvendas.objects.using(banco).get(
            cont_cont=cont_cont,
            cont_empr=empresa_id,
            cont_fili=filial_id
        )
        
        data.pop("cont_cont", None)
        data.pop("cont_empr", None)
        data.pop("cont_fili", None)
        
        validate_schema(data, CONTRATO_CREATE_SCHEMA)
        for key, value in data.items():
            setattr(contrato, key, value)
        contrato.save()
        return contrato
    
    @staticmethod
    def delete_contrato(cont_cont, context):
        banco = get_licenca_db_config(context["request"])
        empresa_id = context["empresa_id"]
        filial_id = context["filial_id"]
        contrato = Contratosvendas.objects.using(banco).get(
            cont_cont=cont_cont,
            cont_empr=empresa_id,
            cont_fili=filial_id
        )
        contrato.delete()
        return {"message": "Contrato deletado com sucesso."}

