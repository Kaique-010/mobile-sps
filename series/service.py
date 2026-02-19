from .models import Series

class SeriesService:
    @staticmethod
    def get_series(empresa: int, filial: int):
        return Series.objects.filter(seri_empr=empresa, seri_fili=filial)
    
    @staticmethod
    def get_series_by_type(empresa: int, filial: int, tipo: str):
        return Series.objects.filter(seri_empr=empresa, seri_fili=filial, seri_nome=tipo)
    
    @staticmethod
    def obter_series_produtor_rural(empresa: int, filial: int, tipo: str = 'PR'):
        if tipo != 'PR':
            raise ValueError("O tipo deve ser 'PR' para Produtor Rural.")
        
        return Series.objects.filter(
            seri_empr=empresa,
            seri_fili=filial,
            seri_nome=tipo,
            seri_codi__gte='920',
            seri_codi__lte='969',
        )
