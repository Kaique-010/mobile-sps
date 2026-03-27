from transportes.models import Cte, Mdfe
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


class NumeracaoMdfeService:
    def __init__(self, empresa_id, filial_id, serie=1, slug=None):
        self.empresa_id = empresa_id
        self.filial_id = filial_id
        self.serie = int(serie or 1)
        self.slug = slug

    def proximo_numero(self) -> int:
        max_num = (
            Mdfe.objects.using(self.slug)
            .filter(mdf_empr=self.empresa_id, mdf_fili=self.filial_id, mdf_seri=self.serie)
            .aggregate(Max("mdf_nume"))
            .get("mdf_nume__max")
        )
        return int(max_num or 0) + 1


class SequencialService:
    @staticmethod
    def proximo_id(model, field_name: str, slug=None) -> int:
        max_id = model.objects.using(slug).aggregate(Max(field_name)).get(f"{field_name}__max")
        return int(max_id or 0) + 1
