from .models import Controlevisita, ItensVisita
from Orcamentos.models import Orcamentos, ItensOrcamento
from Pisos.models import Orcamentopisos, Itensorcapisos
from django.db.models import Max
from core.decorator import get_modulos_usuario_db
from Pisos.services.utils_service import DadosEntidadesService

def exportar_visita_para_orcamento(visita: Controlevisita, banco: str):
    """
    Cria um orçamento a partir de uma visita e seus itens.
    """
    # Validar se já tem orçamento
    if visita.ctrl_nume_orca:
        raise ValueError("Essa visita já possui um orçamento vinculado.")


    itens_visita = ItensVisita.objects.using(banco).filter(item_visita=visita)
    if not itens_visita.exists():
        raise ValueError("Nenhum item encontrado para esta visita.")

    max_numero = Orcamentos.objects.using(banco).filter(
        pedi_empr=visita.ctrl_empresa.pk,
        pedi_fili=visita.ctrl_filial.pk  
    ).aggregate(Max('pedi_nume'))['pedi_nume__max'] or 0

    # Criar orçamento
    orc = Orcamentos.objects.using(banco).create(
        pedi_empr=visita.ctrl_empresa.pk,
        pedi_fili=visita.ctrl_filial.pk,
        pedi_nume=max_numero + 1,
        pedi_forn=str(visita.ctrl_cliente.pk) if visita.ctrl_cliente else '',
        pedi_data=visita.ctrl_data,
        pedi_vend=str(visita.ctrl_vendedor.pk) if visita.ctrl_vendedor else '',
        pedi_obse=f"Orçamento gerado da visita {visita.ctrl_numero}",
        pedi_topr=0, 
        pedi_tota=0,
    )

    # Criar itens do orçamento
    total = 0
    itens = []
    for idx, item in enumerate(itens_visita, start=1):
        tota = (item.item_quan or 0) * (item.item_unit or 0)
        total += tota
        itens.append(ItensOrcamento(
            iped_empr=visita.ctrl_empresa.pk,
            iped_fili=visita.ctrl_filial.pk,
            iped_pedi=str(orc.pedi_nume),
            iped_item=idx,
            iped_prod=item.item_prod, 
            iped_quan=item.item_quan,
            iped_unit=item.item_unit,
            iped_suto=tota,  
            iped_tota=tota,
            iped_desc=item.item_desc or 0,
            iped_unli=tota,  
            iped_data=item.item_data or visita.ctrl_data,
        ))

    ItensOrcamento.objects.using(banco).bulk_create(itens)
    
    # Atualizar totais
    orc.pedi_tota = total
    orc.pedi_topr = total  
    orc.save(using=banco, update_fields=["pedi_tota", "pedi_topr"])

    # Vincular orçamento à visita
    visita.ctrl_nume_orca = orc.pedi_nume
    visita.save(using=banco, update_fields=["ctrl_nume_orca"])

    return orc

def exportar_visita_para_orcamento_pisos(visita: Controlevisita, banco: str, request=None):
    """
    Cria um orçamento de pisos a partir de uma visita e seus itens.
    """
    # Validar se já tem orçamento
    
    if visita.ctrl_nume_orca:
        raise ValueError("Essa visita já possui um orçamento vinculado.")

    # Buscar itens da visita
    itens_visita = ItensVisita.objects.using(banco).filter(item_visita=visita)
    if not itens_visita.exists():
        raise ValueError("Nenhum item encontrado para esta visita.")

    # Gerar próximo número do orçamento de pisos
    max_numero = Orcamentopisos.objects.using(banco).filter(
        orca_empr=visita.ctrl_empresa.pk,
        orca_fili=visita.ctrl_filial.pk
    ).aggregate(Max('orca_nume'))['orca_nume__max'] or 0

    # Criar orçamento de pisos
    orc_pisos = Orcamentopisos.objects.using(banco).create(
        orca_empr=visita.ctrl_empresa.pk,
        orca_fili=visita.ctrl_filial.pk,
        orca_nume=max_numero + 1,
        orca_clie=visita.ctrl_cliente.pk if visita.ctrl_cliente else None,
        orca_data=visita.ctrl_data,
        orca_vend=visita.ctrl_vendedor.pk if visita.ctrl_vendedor else None,
        orca_obse=f"Orçamento de pisos gerado da visita {visita.ctrl_numero}",
        orca_tota=0,
        orca_stat=0,  # Status inicial
    )

    # Preencher dados da entidade se request foi fornecido
    if request and visita.ctrl_cliente:
        orc_pisos = DadosEntidadesService.preencher_dados_cliente(orc_pisos, request)

    # Criar itens do orçamento de pisos
    total = 0
    itens = []
    for idx, item in enumerate(itens_visita, start=1):
        item_subtotal = (item.item_quan or 0) * (item.item_unit or 0)
        total += item_subtotal
        
        itens.append(Itensorcapisos(
            item_empr=visita.ctrl_empresa.pk,
            item_fili=visita.ctrl_filial.pk,
            item_orca=orc_pisos.orca_nume,
            item_ambi=1,  # Ambiente padrão
            item_prod=item.item_prod,
            item_quan=item.item_quan,
            item_unit=item.item_unit,
            item_suto=item_subtotal,
            item_obse=item.item_obse or '',
            item_nume=idx,
            item_desc=item.item_desc or 0,
        ))

    Itensorcapisos.objects.using(banco).bulk_create(itens)
    
    # Atualizar totais
    orc_pisos.orca_tota = total
    orc_pisos.save(using=banco, update_fields=["orca_tota"])

    # Vincular orçamento à visita
    visita.ctrl_nume_orca = orc_pisos.orca_nume
    visita.save(using=banco, update_fields=["ctrl_nume_orca"])

    return orc_pisos

def verificar_modulo_pisos_liberado(request):
    """
    Verifica se o módulo de Pisos está liberado para o usuário/empresa.
    """
    try:
        modulos = get_modulos_usuario_db(request)
        return 'Pisos' in modulos
    except Exception:
        return False