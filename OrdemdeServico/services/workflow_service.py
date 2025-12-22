from ..dominio.workflow import WorkflowOrdem
from ..repositorios.workflow_repo import (
    obter_setores_validos, 
    obter_setores_anteriores_validos,
    obter_objetos_proximos_setores,
    obter_objetos_setores_anteriores
)
from ..repositorios.historico_repo import registrar_historico

def avancar_setor(ordem_model, setor_destino, usuario, banco):
    setores_validos = obter_setores_validos(
        setor_atual=ordem_model.orde_seto,
        banco=banco
    )

    workflow = WorkflowOrdem(ordem_model.orde_seto)
    workflow.validar_avanco(setor_destino, setores_validos)

    setor_origem = ordem_model.orde_seto
    ordem_model.orde_seto = setor_destino
    ordem_model.save(using=banco, update_fields=["orde_seto"])

    registrar_historico(
        ordem=ordem_model,
        setor_origem=setor_origem,
        setor_destino=setor_destino,
        usuario=usuario,
        banco=banco
    )

    return ordem_model

def retornar_setor(ordem_model, setor_origem, usuario, banco):
    """
    Retorna a ordem para um setor anterior.
    """
    setores_validos = obter_setores_anteriores_validos(
        setor_atual=ordem_model.orde_seto,
        banco=banco
    )
    
    # Validação simples: se o setor de origem está na lista de setores que levam ao atual
    # Nota: No retorno, "setor_origem" é para onde queremos ir (voltar).
    if setor_origem not in setores_validos:
         # Tenta converter para int caso venha como string
        try:
            if int(setor_origem) not in setores_validos:
                 raise ValueError(f"Não é possível retornar para o setor {setor_origem}")
        except ValueError:
            raise ValueError(f"Não é possível retornar para o setor {setor_origem}")

    setor_atual = ordem_model.orde_seto
    ordem_model.orde_seto = setor_origem
    ordem_model.save(using=banco, update_fields=["orde_seto"])

    registrar_historico(
        ordem=ordem_model,
        setor_origem=setor_atual,
        setor_destino=setor_origem,
        usuario=usuario,
        banco=banco
    )

    return ordem_model

def listar_proximos_setores(ordem_model, banco):
    return obter_objetos_proximos_setores(ordem_model.orde_seto, banco)

def listar_setores_anteriores(ordem_model, banco):
    return obter_objetos_setores_anteriores(ordem_model.orde_seto, banco)
