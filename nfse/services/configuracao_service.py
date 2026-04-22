from nfse.models import NfseConfiguracaoMunicipio


class ConfiguracaoMunicipioService:
    @staticmethod
    def obter_por_municipio(context, codigo_municipio: str):
        return (
            NfseConfiguracaoMunicipio.objects.using(context.db_alias)
            .filter(
                nfmc_empr=context.empresa_id,
                nfmc_fili=context.filial_id,
                nfmc_codi_muni=codigo_municipio
            )
            .first()
        )