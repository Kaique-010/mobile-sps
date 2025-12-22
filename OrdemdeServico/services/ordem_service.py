from ..repositorios import ordem_repo
from ..services import total_service
from django.db import transaction

def criar_ordem_servico(dados, pecas_data, servicos_data, usuario, banco):
    """
    Cria uma nova ordem de serviço com suas peças e serviços.
    """
    # Regra de negócio: Definir número da ordem se não vier (ou validar)
    # Por enquanto, seguindo a lógica do antigo viewset, o número vem no payload se for manual.
    # Se precisarmos gerar:
    if not dados.get('orde_nume'):
        # TODO: Implementar geração automática quando sair do modo manual
        pass

    with transaction.atomic(using=banco):
        ordem = ordem_repo.criar_ordem(dados, banco)
        
        if pecas_data:
            ordem_repo.sync_pecas(ordem, pecas_data, banco)
        
        if servicos_data:
            ordem_repo.sync_servicos(ordem, servicos_data, banco)
            
        # Calcular total inicial
        if hasattr(ordem, 'calcular_total'):
            try:
                ordem.calcular_total(banco=banco)
            except TypeError:
                # Fallback se o método não aceitar banco ainda
                ordem.calcular_total()
        ordem.save(using=banco)
        
    return ordem

def atualizar_ordem_servico(ordem, dados, pecas_data, servicos_data, usuario, banco):
    """
    Atualiza uma ordem de serviço existente.
    """
    with transaction.atomic(using=banco):
        ordem = ordem_repo.atualizar_ordem(ordem, dados, banco)
        
        if pecas_data is not None: # Se None, não mexe. Se lista vazia, limpa/atualiza.
            ordem_repo.sync_pecas(ordem, pecas_data, banco)
            
        if servicos_data is not None:
            ordem_repo.sync_servicos(ordem, servicos_data, banco)
            
        # Recalcular total
        if hasattr(ordem, 'calcular_total'):
            try:
                ordem.calcular_total(banco=banco)
            except TypeError:
                ordem.calcular_total()
        ordem.save(using=banco)
        
    return ordem
