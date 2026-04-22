from nfse.exceptions import NfseClientError
from nfse.services.configuracao_service import ConfiguracaoMunicipioService
from nfse.services.persistencia_service import PersistenciaNfseService
from nfse.services.router_service import RouterNfseService


class ConsultaNfseService:
    @staticmethod
    def consultar(context, nfse_id: int):
        nfse = PersistenciaNfseService.obter_nfse(context, nfse_id)
        if not nfse:
            raise ValueError('NFS-e não encontrada')

        config = ConfiguracaoMunicipioService.obter_por_municipio(
            context,
            nfse.nfse_muni_codi
        )
        client = RouterNfseService.obter_client(config)

        payload = {
            'numero': nfse.nfse_nume,
            'protocolo': nfse.nfse_prot,
            'rps_numero': nfse.nfse_rps_nume,
            'rps_serie': nfse.nfse_rps_seri,
        }

        try:
            retorno = client.consultar(**payload)

            PersistenciaNfseService.atualizar_consulta(context, nfse, retorno)
            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'consulta',
                payload=payload,
                resposta=retorno,
                descricao='Consulta de NFS-e realizada com sucesso'
            )
            return retorno

        except NfseClientError as erro:
            PersistenciaNfseService.marcar_erro(
                context,
                nfse,
                erro,
                resposta=erro.resposta,
                xml_retorno=erro.xml_retorno,
            )
            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'erro_consulta',
                payload=erro.payload or payload,
                resposta=erro.resposta,
                descricao=str(erro)
            )
            raise

        except Exception as erro:
            PersistenciaNfseService.marcar_erro(context, nfse, erro)
            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'erro_consulta',
                payload=payload,
                descricao=str(erro)
            )
            raise