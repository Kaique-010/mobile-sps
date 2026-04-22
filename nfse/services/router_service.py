class RouterNfseService:
    @staticmethod
    def obter_client(config):
        if not config:
            raise ValueError('Configuração do município não encontrada')

        if config.nfmc_usa_naci:
            from nfse.clients.nacional_client import NacionalClient
            return NacionalClient(config=config)

        if config.nfmc_prov == 'elotech':
            from nfse.clients.ponta_grossa_elotech_client import PontaGrossaElotechClient
            return PontaGrossaElotechClient(config=config)

        if config.nfmc_prov == 'abrasf':
            from nfse.clients.abrasf_client import AbrasfClient
            return AbrasfClient(config=config)

        raise ValueError(f'Provider not supported: {config.nfmc_prov}')