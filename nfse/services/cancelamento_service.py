from nfse.exceptions import NfseClientError
from nfse.services.configuracao_service import ConfiguracaoMunicipioService
from nfse.services.persistencia_service import PersistenciaNfseService
from nfse.services.router_service import RouterNfseService


class CancelamentoNfseService:
    @staticmethod
    def cancelar(context, nfse_id: int, motivo: str):
        nfse = PersistenciaNfseService.obter_nfse(context, nfse_id)
        if not nfse:
            raise ValueError('NFS-e não encontrada')

        if not motivo:
            raise ValueError('Informe o motivo do cancelamento')

        config = ConfiguracaoMunicipioService.obter_por_municipio(
            context,
            nfse.nfse_muni_codi
        )
        client = RouterNfseService.obter_client(config)

        payload = {
            'numero': nfse.nfse_nume,
            'codigo_verificacao': nfse.nfse_codi_veri,
            'motivo': motivo,
        }

        try:
            retorno = client.cancelar(**payload)

            PersistenciaNfseService.marcar_cancelada(context, nfse, resposta=retorno)
            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'cancelamento',
                payload=payload,
                resposta=retorno,
                descricao='NFS-e cancelada com sucesso'
            )
            return nfse

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
                'erro_cancelamento',
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
                'erro_cancelamento',
                payload=payload,
                descricao=str(erro)
            )
            raise