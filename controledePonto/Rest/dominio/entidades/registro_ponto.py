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
