from nfse.clients.base_client import BaseNfseClient


class NacionalClient(BaseNfseClient):
    def emitir(self, data: dict):
        return {
            'numero': '12345',
            'codigo_verificacao': 'ABC123',
            'protocolo': 'PROTO-001',
            'status': 'emitida',
        }

    def consultar(self, **kwargs):
        return {
            'status': 'emitida',
            'numero': kwargs.get('numero'),
        }

    def cancelar(self, **kwargs):
        return {
            'status': 'cancelada',
            'motivo': kwargs.get('motivo'),
        }