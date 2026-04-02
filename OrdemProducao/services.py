from django.utils import timezone

from Entidades.models import Entidades

from .models import Ordemproducao, Ordemprodfotos, Ordemproditens, Ordemprodmate, Ordemprodetapa


class OrdemProducaoService:
    @staticmethod
    def listar_ordens(*, using):
        return Ordemproducao.objects.using(using).all()

    @staticmethod
    def buscar_cliente_nome(*, using, ordem):
        if not ordem.orpr_clie:
            return None
        entidade = Entidades.objects.using(using).filter(
            enti_clie=ordem.orpr_clie,
            enti_empr=ordem.orpr_empr,
        ).first()
        return entidade.enti_nome if entidade else None

    @staticmethod
    def iniciar_producao(*, ordem, using):
        ordem.orpr_stat = 2
        ordem.save(using=using, update_fields=["orpr_stat"])
        return ordem

    @staticmethod
    def finalizar_ordem(*, ordem, using):
        ordem.orpr_stat = 3
        ordem.orpr_fech = timezone.now()
        ordem.save(using=using, update_fields=["orpr_stat", "orpr_fech"])
        return ordem

    @staticmethod
    def dashboard(*, using):
        qs = OrdemProducaoService.listar_ordens(using=using)
        ordens_por_tipo = {tipo: qs.filter(orpr_tipo=tipo).count() for tipo in ["1", "2", "3", "4"]}
        return {
            "total_ordens": qs.count(),
            "ordens_abertas": qs.filter(orpr_stat=1).count(),
            "ordens_producao": qs.filter(orpr_stat=2).count(),
            "ordens_finalizadas": qs.filter(orpr_stat=3).count(),
            "ordens_por_tipo": ordens_por_tipo,
            "ordens_atrasadas": qs.filter(orpr_prev__lt=timezone.now(), orpr_stat__in=[1, 2]).count(),
        }


class OrdemProducaoFilhosService:
    @staticmethod
    def listar_fotos(*, ordem, using):
        return Ordemprodfotos.objects.using(using).filter(
            orpr_codi=ordem.orpr_codi,
            orpr_empr=ordem.orpr_empr,
            orpr_fili=ordem.orpr_fili,
        )

    @staticmethod
    def listar_itens(*, ordem, using):
        return Ordemproditens.objects.using(using).filter(
            orpr_codi=ordem.orpr_codi,
            orpr_fili=ordem.orpr_fili,
        )

    @staticmethod
    def listar_materiais(*, ordem, using):
        return Ordemprodmate.objects.using(using).filter(orpm_orpr=ordem.orpr_codi)

    @staticmethod
    def listar_etapas(*, ordem, using):
        return Ordemprodetapa.objects.using(using).filter(opet_orpr=ordem.orpr_codi)
