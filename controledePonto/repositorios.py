from typing import Optional, List
from controledePonto.Rest.dominio.entidades.registro_ponto import RegistroPonto as RegistroPontoEntidade
from controledePonto.Rest.dominio.portas.repositorio_ponto import RepositorioPonto
from .models import RegistroPonto as RegistroPontoModelo


class RepositorioPontoModelo(RepositorioPonto):
    def __init__(self, banco: Optional[str] = None):
        self.banco = banco

    def registrar(self, registro: RegistroPontoEntidade) -> RegistroPontoEntidade:
        modelo = RegistroPontoModelo.objects.using(self.banco).create(
            colaborador_id=registro.colaborador_id,
            documento=registro.documento,
            data_hora=registro.data_hora,
            tipo=registro.tipo
        )
        return RegistroPontoEntidade(
            colaborador_id=modelo.colaborador_id,
            documento=modelo.documento,
            data_hora=modelo.data_hora,
            tipo=modelo.tipo,
            id=modelo.id
        )

    def listar_por_id(self, colaborador_id: int) -> Optional[List[RegistroPontoEntidade]]:
        qs = RegistroPontoModelo.objects.using(self.banco).filter(colaborador_id=colaborador_id)
        if not qs.exists():
            return None
        return [
            RegistroPontoEntidade(
                id=col.id,
                colaborador_id=col.colaborador_id,
                documento=col.documento,
                data_hora=col.data_hora,
                tipo=col.tipo
            )
            for col in qs
        ]

    def listar_todos(self) -> List[RegistroPontoEntidade]:
        qs = RegistroPontoModelo.objects.using(self.banco).all().order_by('colaborador_id', 'data_hora')
        return [
            RegistroPontoEntidade(
                id=col.id,
                colaborador_id=col.colaborador_id,
                documento=col.documento,
                data_hora=col.data_hora,
                tipo=col.tipo
            )
            for col in qs
        ]

    def remover(self, id: int) -> None:
        RegistroPontoModelo.objects.using(self.banco).filter(id=id).delete()
