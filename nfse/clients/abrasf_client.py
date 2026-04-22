from nfse.clients.base_client import BaseNfseClient


class AbrasfClient(BaseNfseClient):
    def emitir(self, data: dict):
        return {
            'numero': '999',
            'codigo_verificacao': 'ABRASF999',
            'protocolo': 'PROTO-ABRASF',
            'status': 'emitida',
        }

    def consultar(self, **kwargs):
        return {'status': 'emitida'}

    def cancelar(self, **kwargs):
        return {'status': 'cancelada', 'motivo': kwargs.get('motivo')}