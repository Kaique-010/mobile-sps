from abc import ABC, abstractmethod
from typing import List, Optional
from controledePonto.Rest.dominio.entidades.registro_ponto import RegistroPonto


class RepositorioPonto(ABC):
    @abstractmethod
    def listar_por_id(self, id: int) -> Optional[List[RegistroPonto]]:
        pass

    @abstractmethod
    def listar_todos(self) -> List[RegistroPonto]:
        pass

    @abstractmethod
    def registrar(self, registro: RegistroPonto) -> RegistroPonto:
        pass

    @abstractmethod
    def remover(self, id: int) -> None:
        pass
