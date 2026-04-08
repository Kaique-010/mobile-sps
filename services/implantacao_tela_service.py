from core.utils import get_licenca_db_config
from .models import ImplantacaoTela

class ImplantacaoTelaService:

    @staticmethod
    def listar_implantacoes(request):
        db = get_licenca_db_config(request)
        return ImplantacaoTela.objects.using(db).all()

    @staticmethod
    def criar_implantacao(data, request):
        db = get_licenca_db_config(request)
        implantacao = ImplantacaoTela(**data)
        implantacao.save(using=db)
        return implantacao

    @staticmethod
    def atualizar_implantacao(instance, data, request):
        db = get_licenca_db_config(request)
        for attr, value in data.items():
            setattr(instance, attr, value)
        instance.save(using=db)
        return instance

    @staticmethod
    def deletar_implantacao(instance, request):
        db = get_licenca_db_config(request)
        instance.delete(using=db)