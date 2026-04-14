from datetime import date


def validar_datas_titulo(titu_emis=None, titu_venc=None, *, hoje=None):
    """Retorna avisos de data para títulos financeiros sem bloquear o salvamento."""
    avisos = []
    data_atual = hoje or date.today()

    if titu_emis and titu_emis < data_atual:
        avisos.append('Data de emissão anterior à data atual.')

    if titu_venc and titu_venc < data_atual:
        avisos.append('Data de vencimento anterior à data atual.')

    if titu_emis and titu_venc and titu_venc < titu_emis:
        avisos.append('Data de vencimento anterior à data de emissão.')

    return avisos
