from django.db.models import Max
from transportes.models import Veiculos

class VeiculosService:
    @staticmethod
    def gerar_sequencial(empresa_id, transportadora_id, using='default'):
        max_sequ = Veiculos.objects.using(using).filter(
            veic_empr=empresa_id, 
            veic_tran=transportadora_id
        ).aggregate(Max('veic_sequ'))['veic_sequ__max']
        
        return (max_sequ or 0) + 1

    @staticmethod
    def create_veiculo(data, using='default'):
        veiculo = Veiculos(**data)
        veiculo.save(using=using)
        return veiculo

    @staticmethod
    def update_veiculo(veiculo, data, using='default'):
        for key, value in data.items():
            setattr(veiculo, key, value)
        veiculo.save(using=using)
        return veiculo
