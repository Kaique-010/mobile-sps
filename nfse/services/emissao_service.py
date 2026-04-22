from django.db import transaction

from nfse.exceptions import NfseClientError
from nfse.services.configuracao_service import ConfiguracaoMunicipioService
from nfse.services.persistencia_service import PersistenciaNfseService
from nfse.services.router_service import RouterNfseService
from nfse.services.validacao_service import ValidacaoNfseService


class EmissaoNfseService:
    @staticmethod
    @transaction.atomic
    def emitir(context, data: dict):
        ValidacaoNfseService.validar_payload(data)

        payload = dict(data)
        nfse = PersistenciaNfseService.criar_rascunho(context, dict(payload))

        try:
            config = ConfiguracaoMunicipioService.obter_por_municipio(
                context,
                payload['municipio_codigo']
            )
            client = RouterNfseService.obter_client(config)

            xml_envio = None
            if hasattr(client, 'montar_xml_envio_emissao'):
                xml_envio = client.montar_xml_envio_emissao(payload)

            PersistenciaNfseService.salvar_envio(
                context,
                nfse,
                payload=payload,
                xml_envio=xml_envio,
                status='processando'
            )

            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'xml_preparado',
                payload=payload,
                resposta={'xml_envio': xml_envio} if xml_envio else None,
                descricao='XML de envio preparado antes da transmissão'
            )

            retorno = client.emitir(payload)

            PersistenciaNfseService.marcar_emitida(context, nfse, retorno)
            PersistenciaNfseService.registrar_evento(
                context,
                nfse.pk,
                'emissao',
                payload=payload,
                resposta=retorno,
                descricao='NFS-e emitida com sucesso'
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
                'erro_emissao',
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
                'erro_emissao',
                payload=payload,
                descricao=str(erro)
            )
            raise