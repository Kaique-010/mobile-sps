from .models import Series
from typing import Optional

class SeriesService:
    @staticmethod
    def get_series(empresa: int, filial: int, using: Optional[str] = None):
        qs = Series.objects
        if using:
            qs = qs.using(using)
        return qs.filter(seri_empr=empresa, seri_fili=filial)
    
    @staticmethod
    def get_series_by_type(empresa: int, filial: int, tipo: str, using: Optional[str] = None):
        qs = Series.objects
        if using:
            qs = qs.using(using)
        return qs.filter(seri_empr=empresa, seri_fili=filial, seri_nome=tipo)
    
    @staticmethod
    def obter_series_produtor_rural(empresa: int, filial: int, tipo: str = 'PR', using: Optional[str] = None):
        if tipo != 'PR':
            raise ValueError("O tipo deve ser 'PR' para Produtor Rural.")
        
        qs = Series.objects
        if using:
            qs = qs.using(using)
        return qs.filter(
            seri_empr=empresa,
            seri_fili=filial,
            seri_nome=tipo,
            seri_codi__gte='920',
            seri_codi__lte='969',
        )
