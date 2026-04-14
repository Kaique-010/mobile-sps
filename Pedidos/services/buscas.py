from Entidades.models import Entidades


class BuscasEntidadesService:
    @staticmethod
    def buscar_vendedores(*, banco: str, empresa_id: int, busca: str = '', limit: int = 200):
        qs = Entidades.objects.using(banco).filter(
            enti_empr=str(empresa_id),
            enti_tipo_enti__icontains='VE',
        )
        busca = (busca or '').strip()
        if busca:
            if busca.isdigit():
                qs = qs.filter(enti_clie__icontains=busca)
            else:
                qs = qs.filter(enti_nome__icontains=busca)
        return qs.order_by('enti_nome')[: max(1, min(int(limit or 200), 500))]

    @staticmethod
    def buscar_clientes(*, banco: str, empresa_id: int, busca: str = '', limit: int = 200):
        from django.db.models import Q

        qs = Entidades.objects.using(banco).filter(
            enti_empr=str(empresa_id),
            enti_clie__isnull=False,
        ).filter(
            Q(enti_tipo_enti__icontains='CL') | Q(enti_tipo_enti__icontains='AM') | Q(enti_tipo_enti__icontains='FO')
        )
        busca = (busca or '').strip()
        if busca:
            if busca.isdigit():
                qs = qs.filter(enti_clie__icontains=busca)
            else:
                qs = qs.filter(enti_nome__icontains=busca)
        return qs.order_by('enti_nome')[: max(1, min(int(limit or 200), 500))]

    @staticmethod
    def buscar_entidades(*, banco: str, empresa_id: int, busca: str = '', limit: int = 200):
        qs = Entidades.objects.using(banco).filter(
            enti_empr=str(empresa_id),
            enti_clie__isnull=False,
        )
        busca = (busca or '').strip()
        if busca:
            if busca.isdigit():
                qs = qs.filter(enti_clie__icontains=busca)
            else:
                qs = qs.filter(enti_nome__icontains=busca)
        return qs.order_by('enti_nome')[: max(1, min(int(limit or 200), 500))]
