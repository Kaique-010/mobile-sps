from transportes.models import Cte
from django.db import transaction
from django.utils import timezone
from transportes.services.numeracao_service import NumeracaoService

class RascunhoService:
    def __init__(self, user, empresa, filial, slug=None):
        self.user = user
        self.empresa = empresa
        self.filial = filial
        self.slug = slug

    def criar_rascunho(self, dados_iniciais):
        """
        Cria um novo CTe com status RASCUNHO.
        """
        with transaction.atomic(using=self.slug):
            cte = Cte()
            # Handle Empresa assignment (IntegerField)
            if hasattr(self.empresa, 'empr_codi'):
                cte.empresa = self.empresa.empr_codi
            else:
                cte.empresa = self.empresa

            # Handle Filial assignment (IntegerField)
            if hasattr(self.filial, 'empr_codi'):
                cte.filial = self.filial.empr_codi
            else:
                cte.filial = self.filial

            # Tenta pegar o ID do usuário de várias formas possíveis no legacy
            if hasattr(self.user, 'usua_codi'):
                cte.usuario = self.user.usua_codi
            elif hasattr(self.user, 'id'):
                cte.usuario = self.user.id
            
            cte.status = 'RAS'
            cte.modelo = '57' # Modelo padrão CTe
            cte.serie = '1' # Série padrão, idealmente viria de config da filial
            cte.subserie = ''
            numerador = NumeracaoService(cte.empresa, cte.filial, cte.serie, slug=self.slug)
            novo_numero = numerador.proximo_numero()
            cte.numero = novo_numero
            cte.id = str(novo_numero)
            cte.emissao = timezone.now().date()
            cte.hora = timezone.now().time()
            
            # Preencher campos iniciais permitidos
            campos_permitidos = [
                'remetente', 'destinatario', 'motorista', 'veiculo',
                'tomador_servico', 'tipo_servico', 'tipo_cte',
                'forma_emissao', 'tipo_frete', 'observacoes'
            ]
            
            for key, value in dados_iniciais.items():
                if key in campos_permitidos:
                    # Handle entity assignment for IntegerFields
                    if key in ['remetente', 'destinatario', 'motorista', 'veiculo', 'tomador_servico', 'transportadora'] and hasattr(value, 'pk'):
                         setattr(cte, key, value.pk)
                    else:
                         setattr(cte, key, value)
            
            cte.save(using=self.slug)
            
            return cte

    def atualizar_rascunho(self, cte_id, dados_atualizacao):
        """
        Atualiza um rascunho existente.
        """
        try:
            cte = Cte.objects.using(self.slug).get(id=cte_id, empresa=self.empresa, filial=self.filial)
        except Cte.DoesNotExist:
            raise ValueError("CTe não encontrado.")

        if cte.status != 'RAS':
            raise ValueError("Apenas rascunhos podem ser editados.")
            
        with transaction.atomic(using=self.slug):
            # Atualiza campos genéricos
            for key, value in dados_atualizacao.items():
                # Evitar sobrescrever campos de controle
                if key not in ['id', 'empresa', 'filial', 'numero', 'status', 'chave_de_acesso', 'protocolo']:
                    if hasattr(cte, key):
                        setattr(cte, key, value)
            cte.save(using=self.slug)
            return cte

    def excluir_rascunho(self, cte_id):
        """
        Exclui um rascunho.
        """
        try:
            cte = Cte.objects.using(self.slug).get(id=cte_id, empresa=self.empresa, filial=self.filial)
        except Cte.DoesNotExist:
            raise ValueError("CTe não encontrado.")

        if cte.status != 'RAS':
            raise ValueError("Apenas rascunhos podem ser excluídos.")
            
        cte.delete(using=self.slug)
        return True
