from transportes.models import Cte
from django.db.models import Max

class NumeracaoService:
    def __init__(self, empresa_id, filial_id, serie="1", slug=None):
        self.empresa_id = empresa_id
        self.filial_id = filial_id
        self.serie = serie
        self.slug = slug

    def proximo_numero(self) -> int:
        """Retorna o próximo número disponível para a série informada"""
        # Filtra apenas CTes emitidos (não cancelados/inutilizados que ocupam número)
        # Na verdade, cancelados e inutilizados TAMBÉM ocupam número.
        # Então basta pegar o MAX.
        
        max_num = Cte.objects.using(self.slug).filter(
            empresa=self.empresa_id,
            filial=self.filial_id,
            serie=self.serie
        ).aggregate(Max('numero'))['numero__max']
        
        return int(max_num or 0) + 1
