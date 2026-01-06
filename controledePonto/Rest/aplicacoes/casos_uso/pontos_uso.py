from datetime import datetime, date, timedelta
from typing import Optional, List
from controledePonto.Rest.dominio.entidades.registro_ponto import RegistroPonto
from controledePonto.Rest.dominio.portas.repositorio_ponto import RepositorioPonto
from Entidades.models import Entidades 
from core.excecoes import ErroDominio
from core.dominio_handler import tratar_erro, tratar_sucesso

class CasosDeUsoPonto:
    def __init__(self, repositorio: RepositorioPonto):
        self.repositorio = repositorio
    
    
        
    def listar_ponto(self, colaborador_id: int) -> Optional[List[RegistroPonto]]:
        return self.repositorio.listar_por_id(colaborador_id)
    
    
    def listar_todos(self) -> List[RegistroPonto]:
        return self.repositorio.listar_todos()


    def registrar_ponto(self, colaborador_id: int, tipo: str) -> RegistroPonto:
        entidade = Entidades.objects.get(enti_clie=colaborador_id)
        ultimo = self.repositorio.buscar_ultimo(colaborador_id)

        if ultimo and ultimo.tipo == tipo:
            raise ErroDominio('Batida duplicada')
           

        registro = RegistroPonto.criar(
            colaborador_id=entidade.enti_clie,
            documento=entidade.enti_cpf or entidade.enti_cnpj,
            tipo=tipo,
            data_hora=datetime.now(),
        )

        return self.repositorio.registrar(registro)


    
    def total_por_dia(self, colaborador_id: int, data: date) -> timedelta:
        registros = self.repositorio.listar_por_dia(colaborador_id, data)

        total = timedelta()
        entrada = None

        for r in registros:
            if r.tipo == 'ENTRADA':
                entrada = r.data_hora
            elif r.tipo == 'SAIDA' and entrada:
                total += r.data_hora - entrada
                entrada = None

        return total
    
        


    def jornada(self, data: date) -> timedelta:
        return timedelta(hours=8)
    
    
    def banco_de_horas(self, total_trabalhado: timedelta, jornada: timedelta) -> timedelta:
        return total_trabalhado - jornada
