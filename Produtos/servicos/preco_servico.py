from django.utils import timezone
from ..models import Tabelaprecos, Tabelaprecoshist

def criar_preco_com_historico(banco, dados_preco, user=None):
    """
    Cria um novo preço e registra o histórico.
    """
    instance = Tabelaprecos.objects.using(banco).create(**dados_preco)
    
    hist_data = {
        'tabe_empr': instance.tabe_empr,
        'tabe_fili': instance.tabe_fili,
        'tabe_prod': instance.tabe_prod,
        'tabe_data_hora': timezone.now(),
        'tabe_hist': "Criação de preços via API",
        'tabe_perc_reaj': dados_preco.get('tabe_perc_reaj'),
        'tabe_prco_novo': instance.tabe_prco,
        'tabe_avis_novo': instance.tabe_avis,
        'tabe_apra_novo': instance.tabe_apra,
    }
    
    Tabelaprecoshist.objects.using(banco).create(**hist_data)
    return instance

def atualizar_preco_com_historico(banco, instance, novos_dados, user=None):
    """
    Atualiza um preço existente e registra o histórico das alterações.
    """
    # Guardar valores antigos
    old_values = {
        'tabe_prco': instance.tabe_prco,
        'tabe_avis': instance.tabe_avis,
        'tabe_apra': instance.tabe_apra,
        'tabe_pipi': instance.tabe_pipi,
        'tabe_fret': instance.tabe_fret,
        'tabe_desp': instance.tabe_desp,
        'tabe_cust': instance.tabe_cust,
        'tabe_cuge': instance.tabe_cuge,
        'tabe_icms': instance.tabe_icms,
        'tabe_impo': instance.tabe_impo,
        'tabe_marg': instance.tabe_marg,
        'tabe_praz': instance.tabe_praz,
        'tabe_valo_st': instance.tabe_valo_st,
    }

    # Criar histórico textual
    historico = "Alteração de preços via API"
    if 'tabe_prco' in novos_dados and novos_dados['tabe_prco'] != old_values['tabe_prco']:
        historico += f"\nPreço Normal: R$ {old_values['tabe_prco'] or 0:.2f} -> R$ {novos_dados['tabe_prco']:.2f}"
    if 'tabe_avis' in novos_dados and novos_dados['tabe_avis'] != old_values['tabe_avis']:
        historico += f"\nPreço à Vista: R$ {old_values['tabe_avis'] or 0:.2f} -> R$ {novos_dados['tabe_avis']:.2f}"
    if 'tabe_apra' in novos_dados and novos_dados['tabe_apra'] != old_values['tabe_apra']:
        historico += f"\nPreço a Prazo: R$ {old_values['tabe_apra'] or 0:.2f} -> R$ {novos_dados['tabe_apra']:.2f}"

    # Dados para o histórico estruturado
    hist_data = {
        'tabe_empr': instance.tabe_empr,
        'tabe_fili': instance.tabe_fili,
        'tabe_prod': instance.tabe_prod,
        'tabe_data_hora': timezone.now(),
        'tabe_hist': historico,
        'tabe_perc_reaj': novos_dados.get('tabe_perc_reaj'),
        # Valores anteriores
        'tabe_prco_ante': old_values['tabe_prco'],
        'tabe_avis_ante': old_values['tabe_avis'],
        'tabe_apra_ante': old_values['tabe_apra'],
        'tabe_pipi_ante': old_values['tabe_pipi'],
        'tabe_fret_ante': old_values['tabe_fret'],
        'tabe_desp_ante': old_values['tabe_desp'],
        'tabe_cust_ante': old_values['tabe_cust'],
        'tabe_cuge_ante': old_values['tabe_cuge'],
        'tabe_icms_ante': old_values['tabe_icms'],
        'tabe_impo_ante': old_values['tabe_impo'],
        'tabe_marg_ante': old_values['tabe_marg'],
        'tabe_praz_ante': old_values['tabe_praz'],
        'tabe_valo_st_ante': old_values['tabe_valo_st'],
        # Novos valores
        'tabe_prco_novo': novos_dados.get('tabe_prco'),
        'tabe_avis_novo': novos_dados.get('tabe_avis'),
        'tabe_apra_novo': novos_dados.get('tabe_apra'),
        'tabe_pipi_novo': novos_dados.get('tabe_pipi'),
        'tabe_fret_novo': novos_dados.get('tabe_fret'),
        'tabe_desp_novo': novos_dados.get('tabe_desp'),
        'tabe_cust_novo': novos_dados.get('tabe_cust'),
        'tabe_cuge_novo': novos_dados.get('tabe_cuge'),
        'tabe_icms_novo': novos_dados.get('tabe_icms'),
        'tabe_impo_novo': novos_dados.get('tabe_impo'),
        'tabe_marg_novo': novos_dados.get('tabe_marg'),
        'tabe_praz_novo': novos_dados.get('tabe_praz'),
        'tabe_valo_st_novo': novos_dados.get('tabe_valo_st'),
    }

    Tabelaprecoshist.objects.using(banco).create(**hist_data)

    # Atualizar o objeto
    for key, value in novos_dados.items():
        setattr(instance, key, value)
    instance.save(using=banco)
    
    return instance
