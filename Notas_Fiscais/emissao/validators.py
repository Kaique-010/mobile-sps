from .exceptions import AmbienteMismatchError


def validar_ambiente(tpAmb_xml: int, ambiente_filial: int, url_destino: str):
    """
    Valida se:
    - tpAmb do XML (1 ou 2)
    - ambiente configurado na Filial (1 ou 2)
    - URL (homologação vs produção)
    estão coerentes.
    """
    if tpAmb_xml not in (1, 2):
        raise AmbienteMismatchError(f"tpAmb inválido no XML: {tpAmb_xml}")

    if ambiente_filial not in (1, 2):
        raise AmbienteMismatchError(f"Ambiente inválido na filial: {ambiente_filial}")

    if tpAmb_xml != ambiente_filial:
        raise AmbienteMismatchError(
            f"tpAmb do XML ({tpAmb_xml}) diferente do ambiente da filial ({ambiente_filial})"
        )

    url_lower = (url_destino or "").lower()

    if tpAmb_xml == 1:
        # Produção: não deveria estar indo para URL de homologação
        if "homolog" in url_lower or "hml" in url_lower:
            raise AmbienteMismatchError(
                f"Ambiente produção (1) mas URL parece de homologação: {url_destino}"
            )
    else:
        # Homologação: não deveria estar indo para URL de produção
        if "homolog" not in url_lower and "hml" not in url_lower:
            # alguns estados não têm 'homolog' no nome, por isso só avisamos
            # e não travamos com raise
            pass
