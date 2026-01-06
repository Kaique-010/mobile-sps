from datetime import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class RegistroPonto:
    colaborador_id: int
    documento: str
    data_hora: datetime
    tipo: str
    id: Optional[int] = None

    @classmethod
    def criar(cls, colaborador_id: int, documento: str, data_hora: datetime, tipo: str, id: Optional[int] = None):
        return cls(
            colaborador_id=colaborador_id,
            documento=documento,
            data_hora=data_hora,
            tipo=tipo,
            id=id,
        )