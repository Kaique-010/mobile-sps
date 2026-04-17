from decimal import Decimal, InvalidOperation

from django.utils import timezone

from ..preco_models import TabelaprecosPromocional, TabelaprecosPromocionalhist


def _filtrar_campos_model(model, dados):
    campos_validos = {f.name for f in model._meta.fields}
    return {k: v for k, v in (dados or {}).items() if k in campos_validos}


def _to_decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fmt_decimal(value, places, *, default="0"):
    dec = _to_decimal(value)
    if dec is None:
        dec = Decimal(default)
    quant = Decimal("1").scaleb(-places)
    try:
        dec = dec.quantize(quant)
    except (InvalidOperation, ValueError):
        dec = Decimal(default).quantize(quant)
    return f"{dec:.{places}f}"


def criar_preco_com_historico(banco, dados_preco, user=None):
    instancia_preco = TabelaprecosPromocional.objects.using(banco).create(
        **_filtrar_campos_model(TabelaprecosPromocional, dados_preco)
    )

    hist_data = {
        'tabe_empr': instancia_preco.tabe_empr,
        'tabe_fili': instancia_preco.tabe_fili,
        'tabe_prod': instancia_preco.tabe_prod,
        'tabe_data_hora': timezone.now(),
        'tabe_hist': "Criação de preços promocionais via Web/Api",
        'tabe_perc_reaj': (dados_preco or {}).get('tabe_perc_reaj'),
        'tabe_prco_novo': instancia_preco.tabe_prco,
        'tabe_avis_novo': instancia_preco.tabe_avis,
        'tabe_apra_novo': instancia_preco.tabe_apra,
        'tabe_desp_novo': instancia_preco.tabe_desp,
        'tabe_cust_novo': instancia_preco.tabe_cust,
        'tabe_cuge_novo': instancia_preco.tabe_cuge,
        'tabe_marg_novo': instancia_preco.tabe_marg,
        'tabe_praz_novo': instancia_preco.tabe_praz,
    }

    TabelaprecosPromocionalhist.objects.using(banco).create(
        **_filtrar_campos_model(TabelaprecosPromocionalhist, hist_data)
    )
    return instancia_preco


def atualizar_preco_com_historico(banco, instancia_preco, novos_dados, user=None):
    novos_dados = _filtrar_campos_model(TabelaprecosPromocional, novos_dados)

    velhos_valores = {
        'tabe_prco': instancia_preco.tabe_prco,
        'tabe_avis': instancia_preco.tabe_avis,
        'tabe_apra': instancia_preco.tabe_apra,
        'tabe_desp': instancia_preco.tabe_desp,
        'tabe_cust': instancia_preco.tabe_cust,
        'tabe_cuge': instancia_preco.tabe_cuge,
        'tabe_marg': instancia_preco.tabe_marg,
        'tabe_praz': instancia_preco.tabe_praz,
        'tabe_perc_reaj': instancia_preco.tabe_perc_reaj,
    }

    historico = "Alteração de preços promocionais via Web/Api"
    if 'tabe_prco' in novos_dados and _to_decimal(novos_dados.get('tabe_prco')) != _to_decimal(velhos_valores.get('tabe_prco')):
        historico += f"\nPreço Normal: R$ {_fmt_decimal(velhos_valores.get('tabe_prco'), 2)} -> R$ {_fmt_decimal(novos_dados.get('tabe_prco'), 2)}"
    if 'tabe_avis' in novos_dados and _to_decimal(novos_dados.get('tabe_avis')) != _to_decimal(velhos_valores.get('tabe_avis')):
        historico += f"\nPreço à Vista: R$ {_fmt_decimal(velhos_valores.get('tabe_avis'), 2)} -> R$ {_fmt_decimal(novos_dados.get('tabe_avis'), 2)}"
    if 'tabe_apra' in novos_dados and _to_decimal(novos_dados.get('tabe_apra')) != _to_decimal(velhos_valores.get('tabe_apra')):
        historico += f"\nPreço a Prazo: R$ {_fmt_decimal(velhos_valores.get('tabe_apra'), 2)} -> R$ {_fmt_decimal(novos_dados.get('tabe_apra'), 2)}"
    if 'tabe_desp' in novos_dados and _to_decimal(novos_dados.get('tabe_desp')) != _to_decimal(velhos_valores.get('tabe_desp')):
        historico += f"\nDespesas: {_fmt_decimal(velhos_valores.get('tabe_desp'), 4)} -> {_fmt_decimal(novos_dados.get('tabe_desp'), 4)}"
    if 'tabe_marg' in novos_dados and _to_decimal(novos_dados.get('tabe_marg')) != _to_decimal(velhos_valores.get('tabe_marg')):
        historico += f"\nMargem: {_fmt_decimal(velhos_valores.get('tabe_marg'), 4)}% -> {_fmt_decimal(novos_dados.get('tabe_marg'), 4)}%"
    if 'tabe_praz' in novos_dados and _to_decimal(novos_dados.get('tabe_praz')) != _to_decimal(velhos_valores.get('tabe_praz')):
        historico += f"\nPrazo: {_fmt_decimal(velhos_valores.get('tabe_praz'), 4)}% -> {_fmt_decimal(novos_dados.get('tabe_praz'), 4)}%"

    hist_data = {
        'tabe_empr': instancia_preco.tabe_empr,
        'tabe_fili': instancia_preco.tabe_fili,
        'tabe_prod': instancia_preco.tabe_prod,
        'tabe_data_hora': timezone.now(),
        'tabe_hist': historico,
        'tabe_perc_reaj': novos_dados.get('tabe_perc_reaj'),
        'tabe_prco_ante': velhos_valores['tabe_prco'],
        'tabe_avis_ante': velhos_valores['tabe_avis'],
        'tabe_apra_ante': velhos_valores['tabe_apra'],
        'tabe_desp_ante': velhos_valores['tabe_desp'],
        'tabe_cust_ante': velhos_valores['tabe_cust'],
        'tabe_cuge_ante': velhos_valores['tabe_cuge'],
        'tabe_marg_ante': velhos_valores['tabe_marg'],
        'tabe_praz_ante': velhos_valores['tabe_praz'],
        'tabe_prco_novo': novos_dados.get('tabe_prco'),
        'tabe_avis_novo': novos_dados.get('tabe_avis'),
        'tabe_apra_novo': novos_dados.get('tabe_apra'),
        'tabe_desp_novo': novos_dados.get('tabe_desp'),
        'tabe_cust_novo': novos_dados.get('tabe_cust'),
        'tabe_cuge_novo': novos_dados.get('tabe_cuge'),
        'tabe_marg_novo': novos_dados.get('tabe_marg'),
        'tabe_praz_novo': novos_dados.get('tabe_praz'),
    }

    TabelaprecosPromocionalhist.objects.using(banco).create(
        **_filtrar_campos_model(TabelaprecosPromocionalhist, hist_data)
    )

    for key, value in novos_dados.items():
        setattr(instancia_preco, key, value)
    instancia_preco.save(using=banco)

    return instancia_preco


def buscar_preco_promocional(*, banco, tabe_empr, tabe_fili, tabe_prod):
    return (
        TabelaprecosPromocional.objects.using(banco)
        .filter(tabe_empr=tabe_empr, tabe_fili=tabe_fili, tabe_prod=tabe_prod)
        .first()
    )


def obter_valor_preco_promocional(*, preco, modalidade=None):
    if not preco:
        return None
    mod = (modalidade or "").lower().strip()
    if mod in {"avista", "a_vista", "vista", "0"}:
        return preco.tabe_avis or preco.tabe_apra or preco.tabe_prco
    if mod in {"prazo", "a_prazo", "1"}:
        return preco.tabe_apra or preco.tabe_avis or preco.tabe_prco
    return preco.tabe_avis or preco.tabe_apra or preco.tabe_prco
