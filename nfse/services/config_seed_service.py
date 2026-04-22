from nfse.models import NfseConfiguracaoMunicipio


class NfseConfigSeedService:
    @staticmethod
    def seed_ponta_grossa(*, banco: str, empresa_id: int, filial_id: int):
        obj, created = NfseConfiguracaoMunicipio.objects.using(banco).update_or_create(
            nfmc_empr=empresa_id,
            nfmc_fili=filial_id,
            nfmc_codi_muni='4119905',
            defaults={
                'nfmc_nome_muni': 'Ponta Grossa',
                'nfmc_prov': 'elotech',
                'nfmc_usa_naci': False,
                'nfmc_ambi': 'producao',
                'nfmc_url_emis': 'https://pontagrossa.oxy.elotech.com.br/iss-ws/nfseService',
                'nfmc_url_cons': 'https://pontagrossa.oxy.elotech.com.br/iss-ws/nfseService',
                'nfmc_url_canc': 'https://pontagrossa.oxy.elotech.com.br/iss-ws/nfseService',
                'nfmc_wsdl': 'https://pontagrossa.oxy.elotech.com.br/iss-ws/nfse203.wsdl',
                'nfmc_exig_lote': False,
                'nfmc_exig_assi': True,
                'nfmc_seri_rps': '1',
            }
        )
        return obj, created