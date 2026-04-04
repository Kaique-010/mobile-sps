from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from core.utils import get_licenca_db_config
from controledePonto.Rest.aplicacoes.casos_uso.pontos_uso import CasosDeUsoPonto
from controledePonto.repositorios import RepositorioPontoModelo


class RegistroPontoService:
    """Camada de serviço compartilhada entre REST e Web."""

    def __init__(self, request=None, banco: Optional[str] = None):
        self.banco = banco or (get_licenca_db_config(request) if request is not None else "default")
        self.repositorio = RepositorioPontoModelo(banco=self.banco)
        self.casos_uso = CasosDeUsoPonto(self.repositorio)

    def listar(self, colaborador_id: Optional[int] = None):
        if colaborador_id:
            return self.casos_uso.listar_ponto(colaborador_id) or []
        return self.casos_uso.listar_todos()

    def registrar(self, colaborador_id: int, tipo: str):
        return self.casos_uso.registrar_ponto(colaborador_id=colaborador_id, tipo=tipo)

    def total_por_dia(self, colaborador_id: int, data_ref: date):
        return self.casos_uso.total_por_dia(colaborador_id=colaborador_id, data=data_ref)

    def banco_de_horas(self, colaborador_id: int, data_ref: date) -> Dict[str, Any]:
        total_trabalhado = self.total_por_dia(colaborador_id=colaborador_id, data_ref=data_ref)
        jornada = self.casos_uso.jornada(data_ref)
        saldo = self.casos_uso.banco_de_horas(total_trabalhado=total_trabalhado, jornada=jornada)
        return {
            "total_trabalhado": total_trabalhado,
            "jornada": jornada,
            "banco_de_horas": saldo,
        }
