from ..models import WorkflowSetor

def obter_setores_validos(setor_atual, banco):
    """
    Busca no banco os setores permitidos para avanço.
    """
    if not setor_atual:
        # Se não tem setor atual (início), busca setores de origem 0 ou inicial
        return list(WorkflowSetor.objects.using(banco).filter(
            wkfl_seto_orig=0,
            wkfl_ativo=True
        ).values_list('wkfl_seto_dest', flat=True))

    return list(WorkflowSetor.objects.using(banco).filter(
        wkfl_seto_orig=setor_atual,
        wkfl_ativo=True
    ).values_list('wkfl_seto_dest', flat=True))

def obter_setores_anteriores_validos(setor_atual, banco):
    """
    Busca no banco os setores permitidos para retorno.
    """
    if not setor_atual:
        return []

    return list(WorkflowSetor.objects.using(banco).filter(
        wkfl_seto_dest=setor_atual,
        wkfl_ativo=True
    ).values_list('wkfl_seto_orig', flat=True))

def obter_objetos_proximos_setores(setor_atual, banco):
    """
    Retorna os objetos WorkflowSetor completos para os próximos passos.
    """
    origem = setor_atual if setor_atual else 0
    return WorkflowSetor.objects.using(banco).filter(
        wkfl_seto_orig=origem,
        wkfl_ativo=True
    ).order_by('wkfl_orde')

def obter_objetos_setores_anteriores(setor_atual, banco):
    """
    Retorna os objetos WorkflowSetor completos para os passos anteriores.
    """
    if not setor_atual:
        return WorkflowSetor.objects.none()
        
    return WorkflowSetor.objects.using(banco).filter(
        wkfl_seto_dest=setor_atual,
        wkfl_ativo=True
    ).order_by('wkfl_orde')
