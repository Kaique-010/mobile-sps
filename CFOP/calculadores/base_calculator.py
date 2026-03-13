from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP


class BaseCalculator(ABC):

    D100 = Decimal("100")

    def _d(self, v, casas=2):
        if v is None:
            return None

        if not isinstance(v, Decimal):
            v = Decimal(str(v))

        return v.quantize(
            Decimal(10) ** -casas,
            ROUND_HALF_UP
        )

    @abstractmethod
    def calcular(self, ctx, base):
        pass