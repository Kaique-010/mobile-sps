from datetime import datetime
from typing import Optional, List
from controledePonto.Rest.dominio.entidades.registro_ponto import RegistroPonto
from controledePonto.Rest.dominio.portas.repositorio_ponto import RepositorioPonto
from Entidades.models import Entidades 

class CasosDeUsoPonto:
    def __init__(self, repositorio: RepositorioPonto):
        self.repositorio = repositorio
        

    def registrar_ponto(self, colaborador_id: int, tipo: str) -> RegistroPonto:
        entidade = Entidades.objects.get(enti_clie=colaborador_id)

        registro = RegistroPonto(
            colaborador_id=entidade.enti_clie,
            documento=entidade.enti_cpf or entidade.enti_cnpj,
            data_hora=datetime.now(),
            tipo=tipo,
        )

        return self.repositorio.registrar(registro)

        
    def listar_ponto(self, colaborador_id: int) -> Optional[List[RegistroPonto]]:
        return self.repositorio.listar_por_id(colaborador_id)
    
    def listar_todos(self) -> List[RegistroPonto]:
        return self.repositorio.listar_todos()
