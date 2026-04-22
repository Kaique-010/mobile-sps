class BaseNfseClient:
    def __init__(self, config):
        self.config = config

    def emitir(self, data: dict):
        raise NotImplementedError

    def consultar(self, **kwargs):
        raise NotImplementedError

    def cancelar(self, **kwargs):
        raise NotImplementedError