from ..models import (
    Ordemservico, 
    Ordemservicopecas, 
    Ordemservicoservicos,
    Ordemservicoimgantes,
    Ordemservicoimgdurante,
    Ordemservicoimgdepois
)
from ..utils import get_next_item_number_sequence, get_next_service_id

def buscar_ordem_por_numero(numero, banco):
    """Busca uma OS pelo número."""
    try:
        return Ordemservico.objects.using(banco).get(orde_nume=numero)
    except Ordemservico.DoesNotExist:
        return None

def criar_ordem(dados, banco):
    """Cria uma nova ordem de serviço."""
    return Ordemservico.objects.using(banco).create(**dados)

def atualizar_ordem(ordem, dados, banco):
    """Atualiza uma ordem existente."""
    for campo, valor in dados.items():
        setattr(ordem, campo, valor)
    ordem.save(using=banco)
    return ordem

def sync_pecas(ordem, pecas_data, banco):
    """Sincroniza as peças da ordem."""
    ids_enviados = []
    for item in pecas_data:
        item['peca_empr'] = ordem.orde_empr
        item['peca_fili'] = ordem.orde_fili
        item['peca_orde'] = ordem.orde_nume
        
        peca_id = item.get('peca_id')
        
        # Se não tiver ID, tenta buscar pelo código da peça na mesma ordem para atualizar
        if not peca_id and item.get('peca_codi'):
            existing = Ordemservicopecas.objects.using(banco).filter(
                peca_empr=ordem.orde_empr,
                peca_fili=ordem.orde_fili,
                peca_orde=ordem.orde_nume,
                peca_codi=item['peca_codi']
            ).first()
            if existing:
                peca_id = existing.peca_id
                item['peca_id'] = peca_id

        if peca_id:
            # Update existing
            obj, _ = Ordemservicopecas.objects.using(banco).update_or_create(
                peca_id=peca_id,
                defaults=item
            )
            ids_enviados.append(obj.peca_id)
        else:
            # Create new
            if 'peca_id' in item:
                del item['peca_id']

            item['peca_id'] = get_next_item_number_sequence(
                banco,
                ordem.orde_nume,
                ordem.orde_empr,
                ordem.orde_fili,
            )
            obj = Ordemservicopecas.objects.using(banco).create(**item)
            ids_enviados.append(obj.peca_id)

    # Remove peças que não vieram mais
    Ordemservicopecas.objects.using(banco).filter(
        peca_empr=ordem.orde_empr,
        peca_fili=ordem.orde_fili,
        peca_orde=ordem.orde_nume
    ).exclude(peca_id__in=ids_enviados).delete()

def sync_servicos(ordem, servicos_data, banco):
    """Sincroniza os serviços da ordem."""
    ids_enviados = []
    for item in servicos_data:
        item['serv_empr'] = ordem.orde_empr
        item['serv_fili'] = ordem.orde_fili
        item['serv_orde'] = ordem.orde_nume
        
        serv_id = item.get('serv_id')
        
        # Se não tiver ID, tenta buscar pelo código do serviço na mesma ordem para atualizar
        if not serv_id and item.get('serv_codi'):
            existing = Ordemservicoservicos.objects.using(banco).filter(
                serv_empr=ordem.orde_empr,
                serv_fili=ordem.orde_fili,
                serv_orde=ordem.orde_nume,
                serv_codi=item['serv_codi']
            ).first()
            if existing:
                serv_id = existing.serv_id
                item['serv_id'] = serv_id

        if serv_id:
            obj, _ = Ordemservicoservicos.objects.using(banco).update_or_create(
                serv_id=serv_id,
                defaults=item
            )
            ids_enviados.append(obj.serv_id)
        else:
            if 'serv_id' in item:
                del item['serv_id']

            if not item.get('serv_sequ'):
                item['serv_id'], item['serv_sequ'] = get_next_service_id(
                    banco,
                    ordem.orde_nume,
                    ordem.orde_empr,
                    ordem.orde_fili,
                )
            else:
                item['serv_id'], _ = get_next_service_id(
                    banco,
                    ordem.orde_nume,
                    ordem.orde_empr,
                    ordem.orde_fili,
                )
            obj = Ordemservicoservicos.objects.using(banco).create(**item)
            ids_enviados.append(obj.serv_id)

    # Remove serviços que não vieram mais
    Ordemservicoservicos.objects.using(banco).filter(
        serv_empr=ordem.orde_empr,
        serv_fili=ordem.orde_fili,
        serv_orde=ordem.orde_nume
    ).exclude(serv_id__in=ids_enviados).delete()
