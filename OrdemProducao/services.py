import logging
import datetime

from django.utils import timezone
from django.db.models import Max, Q
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Count
from django.db.models.functions import TruncDate

from Entidades.models import Entidades
from django.db import connections

from .models import (
    Etapa,
    Moveetapa,
    MoveEtapaPeso,
    Ordemprodfotos,
    Ordemproditens,
    Ordemprodmate,
    Ordemproducao,
    Ordemproducaoproduto,
    Ourives,
)

logger = logging.getLogger(__name__)


class OrdemProducaoService:
    DATA_MINIMA = datetime.datetime(2000, 1, 1)

    @staticmethod
    def ensure_moveetapeso_table(*, using):
        try:
            table_names = connections[using].introspection.table_names()
            if "moveetapeso" in table_names:
                return True
        except Exception:
            return False

    @staticmethod
    def finalizacao_processada(*, ordem, using):
        entrada_ok = True
        if getattr(ordem, "orpr_prod", None) and getattr(ordem, "orpr_quan", None):
            try:
                from Entradas_Estoque.models import EntradaEstoque

                entrada_ok = EntradaEstoque.objects.using(using).filter(
                    entr_empr=int(ordem.orpr_empr),
                    entr_fili=int(ordem.orpr_fili),
                    entr_prod=str(ordem.orpr_prod)[:10],
                    entr_obse__icontains=f"OP:{int(ordem.orpr_codi)}",
                ).exists()
            except Exception:
                entrada_ok = False

        saldo_ok = True
        try:
            previstos_qs = Ordemproducaoproduto.objects.using(using).filter(orpr_prod_orpr=ordem)
            previstos_existem = previstos_qs.exists()
        except Exception:
            previstos_existem = False

        if previstos_existem:
            if not OrdemProducaoService.ensure_moveetapeso_table(using=using):
                saldo_ok = False
            else:
                try:
                    saldo_ok = MoveEtapaPeso.objects.using(using).filter(moet_peso_oppr=int(ordem.orpr_codi)).exists()
                except Exception:
                    saldo_ok = False

        return bool(entrada_ok and saldo_ok)
        try:
            with connections[using].cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS moveetapeso (
                        id SERIAL PRIMARY KEY,
                        moet_peso_codi numeric(15,4),
                        moet_peso_moet numeric(15,4),
                        moet_peso_prod integer,
                        moet_peso_oppr integer,
                        moet_peso_sald numeric(15,4)
                    );
                    CREATE INDEX IF NOT EXISTS idx_moveetapeso_oppr ON moveetapeso (moet_peso_oppr);
                    """
                )
            return True
        except Exception:
            return False
    @staticmethod
    def listar_ordens(*, using, empresa=None, filial=None):
        qs = Ordemproducao.objects.using(using).all()
        if empresa is not None:
            qs = qs.filter(orpr_empr=int(empresa))
        if filial is not None:
            qs = qs.filter(orpr_fili=int(filial))
        qs = qs.filter(
            orpr_entr__gte=OrdemProducaoService.DATA_MINIMA,
            orpr_prev__gte=OrdemProducaoService.DATA_MINIMA,
        ).filter(
            Q(orpr_fech__isnull=True) | Q(orpr_fech__gte=OrdemProducaoService.DATA_MINIMA)
        ).filter(
            Q(orpr_daen__isnull=True) | Q(orpr_daen__gte=OrdemProducaoService.DATA_MINIMA)
        )
        return qs
    
    @staticmethod
    def proxima_ordem(*, using, empresa, filial):
        qs = Ordemproducao.objects.using(using).filter(orpr_empr=empresa, orpr_fili=filial)
        ultimo = qs.aggregate(Max("orpr_codi"))["orpr_codi__max"] or 0
        return int(ultimo) + 1



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
    def buscar_vendedor(*, using, ordem):
        if not ordem.orpr_vend:
            return None
        entidade = Entidades.objects.using(using).filter(
            enti_clie=ordem.orpr_vend,
            enti_empr=ordem.orpr_empr,
        ).first()
        return entidade.enti_nome if entidade else None

    @staticmethod
    def map_entidades_nomes(*, using, empresa_id, entidade_ids):
        ids = [int(i) for i in set(entidade_ids or []) if str(i).strip().isdigit()]
        if not ids:
            return {}
        qs = (
            Entidades.objects.using(using)
            .filter(enti_empr=int(empresa_id), enti_clie__in=ids)
            .only("enti_clie", "enti_nome")
        )
        return {int(e.enti_clie): e.enti_nome for e in qs}

    @staticmethod
    def autocomplete_clientes(*, using, empresa_id, term):
        term = (term or "").strip()
        qs = Entidades.objects.using(using).filter(
            enti_empr=int(empresa_id),
            enti_tipo_enti__in=["CL", "AM"],
            enti_situ="1",
        )
        if term:
            filters = Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term)
            if term.isdigit():
                filters |= Q(enti_clie=int(term))
            qs = qs.filter(filters)
        qs = qs.order_by("enti_nome")[:20]
        return [{"id": str(e.enti_clie), "text": f"{e.enti_clie} - {e.enti_nome}"} for e in qs]

    @staticmethod
    def autocomplete_vendedores(*, using, empresa_id, term):
        term = (term or "").strip()
        qs = Entidades.objects.using(using).filter(
            enti_empr=int(empresa_id),
            enti_tipo_enti__in=["VE", "AM", "FU"],
            enti_situ="1",
        )
        if term:
            filters = Q(enti_nome__icontains=term) | Q(enti_fant__icontains=term)
            if term.isdigit():
                filters |= Q(enti_clie=int(term))
            qs = qs.filter(filters)
        qs = qs.order_by("enti_nome")[:20]
        return [{"id": str(e.enti_clie), "text": f"{e.enti_clie} - {e.enti_nome}"} for e in qs]

    @staticmethod
    def autocomplete_produtos(*, using, empresa_id, term):
        term = (term or "").strip()
        from Produtos.models import Produtos

        qs = Produtos.objects.using(using).filter(prod_empr=str(empresa_id))
        if term:
            if term.isdigit():
                qs = qs.filter(Q(prod_codi__icontains=term) | Q(prod_codi_nume__icontains=term))
            else:
                qs = qs.filter(Q(prod_nome__icontains=term) | Q(prod_coba__icontains=term))
        qs = qs.only("prod_codi", "prod_nome", "prod_coba").order_by("prod_nome")[:20]
        data = []
        for p in qs:
            codigo = str(getattr(p, "prod_codi", "")).strip()
            nome = str(getattr(p, "prod_nome", "")).strip()
            refe = str(getattr(p, "prod_coba", "")).strip()
            label = f"{codigo} - {nome}"
            if refe:
                label = f"{label} • REF: {refe}"
            data.append({"id": codigo, "text": label})
        return data

    @staticmethod
    def buscar_produto_nome(*, using, empresa_id, codigo):
        codigo = (codigo or "").strip()
        if not codigo:
            return None
        from Produtos.models import Produtos

        p = (
            Produtos.objects.using(using)
            .filter(prod_empr=str(empresa_id), prod_codi=codigo)
            .only("prod_codi", "prod_nome", "prod_coba")
            .first()
        )
        if not p:
            return None
        nome = str(getattr(p, "prod_nome", "")).strip()
        refe = str(getattr(p, "prod_coba", "")).strip()
        label = f"{codigo} - {nome}".strip(" -")
        if refe:
            label = f"{label} • REF: {refe}"
        return label

    @staticmethod
    def map_produtos_nomes(*, using, empresa_id, codigos):
        codigos_limpos = []
        for c in codigos or []:
            s = str(c).strip()
            if not s:
                continue
            codigos_limpos.append(s)
        codigos_limpos = list(dict.fromkeys(codigos_limpos))
        if not codigos_limpos:
            return {}
        from Produtos.models import Produtos

        qs = (
            Produtos.objects.using(using)
            .filter(prod_empr=str(empresa_id), prod_codi__in=codigos_limpos)
            .only("prod_codi", "prod_nome", "prod_coba")
        )
        out = {}
        for p in qs:
            codigo = str(getattr(p, "prod_codi", "")).strip()
            nome = str(getattr(p, "prod_nome", "")).strip()
            refe = str(getattr(p, "prod_coba", "")).strip()
            label = f"{codigo} - {nome}"
            if refe:
                label = f"{label} • REF: {refe}"
            out[codigo] = label
        return out

    @staticmethod
    def iniciar_producao(*, ordem, using):
        ordem.orpr_stat = '1'
        ordem.save(using=using, update_fields=["orpr_stat"])
        return ordem

    @staticmethod
    def finalizar_ordem(*, ordem, using, usua=0):
        with transaction.atomic(using=using):
            if ordem.orpr_stat != '2':
                ordem.orpr_stat = '2'
            if not getattr(ordem, "orpr_fech", None):
                ordem.orpr_fech = timezone.now()
            ordem.save(using=using)
            OrdemProducaoService._registrar_entrada_produto_acabado(ordem=ordem, using=using, usua=usua)
            OrdemProducaoService._registrar_previstos_para_movimentacao(ordem=ordem, using=using)
            return ordem

    @staticmethod
    def _atualizar_saldo_produto(*, using, empresa, filial, produto_codigo, delta):
        try:
            from Produtos.models import Produtos, SaldoProduto
            produto = Produtos.objects.using(using).filter(prod_empr=str(empresa), prod_codi=str(produto_codigo)).first()
            if not produto:
                return
            saldo = SaldoProduto.objects.using(using).filter(produto_codigo=produto, empresa=str(empresa), filial=str(filial)).first()
            if not saldo:
                saldo = SaldoProduto(produto_codigo=produto, empresa=str(empresa), filial=str(filial), saldo_estoque=0)
            saldo.saldo_estoque = (saldo.saldo_estoque or 0) + (delta or 0)
            saldo.save(using=using)
        except Exception:
            pass

    @staticmethod
    def _registrar_entrada_produto_acabado(*, ordem, using, usua=0):
        if not ordem.orpr_prod or not ordem.orpr_quan:
            return
        try:
            from Entradas_Estoque.models import EntradaEstoque
            ja_existe = EntradaEstoque.objects.using(using).filter(
                entr_empr=int(ordem.orpr_empr),
                entr_fili=int(ordem.orpr_fili),
                entr_prod=str(ordem.orpr_prod)[:10],
                entr_obse__icontains=f"OP:{int(ordem.orpr_codi)}",
            ).exists()
            if ja_existe:
                return
            try:
                with transaction.atomic(using=using):
                    proximo = (EntradaEstoque.objects.using(using).aggregate(Max("entr_sequ"))["entr_sequ__max"] or 0) + 1
                    EntradaEstoque.objects.using(using).create(
                        entr_sequ=int(proximo),
                        entr_empr=int(ordem.orpr_empr),
                        entr_fili=int(ordem.orpr_fili),
                        entr_prod=str(ordem.orpr_prod)[:10],
                        entr_enti=str(ordem.orpr_clie)[:10] if getattr(ordem, "orpr_clie", None) else None,
                        entr_data=timezone.now().date(),
                        entr_quan=ordem.orpr_quan or 0,
                        entr_tota=0,
                        entr_obse=f"Referente OP:{int(ordem.orpr_codi)}",
                        entr_usua=int(usua or 0),
                    )
            except IntegrityError:
                logger.exception("Falha de integridade ao registrar entrada de produto acabado (OP=%s)", getattr(ordem, "orpr_codi", None))
                return
            OrdemProducaoService._atualizar_saldo_produto(
                using=using,
                empresa=int(ordem.orpr_empr),
                filial=int(ordem.orpr_fili),
                produto_codigo=str(ordem.orpr_prod),
                delta=ordem.orpr_quan or 0,
            )
        except Exception:
            logger.exception("Falha ao registrar entrada de produto acabado (OP=%s)", getattr(ordem, "orpr_codi", None))

    @staticmethod
    def _registrar_previstos_para_movimentacao(*, ordem, using):
        if not OrdemProducaoService.ensure_moveetapeso_table(using=using):
            return
        try:
            previstos = OrdemProducaoFilhosService.listar_materiais_previstos(ordem=ordem, using=using)
            for prev in previstos:
                try:
                    produto_codigo = getattr(prev.orpr_prod_prod, "prod_codi", None)
                    prod_val = 0
                    if str(produto_codigo).isdigit():
                        prod_val = int(produto_codigo)
                    if not prod_val:
                        continue
                    existe = (
                        MoveEtapaPeso.objects.using(using)
                        .filter(moet_peso_oppr=int(ordem.orpr_codi), moet_peso_prod=int(prod_val))
                        .exists()
                    )
                    if existe:
                        continue
                    MoveEtapaPeso.objects.using(using).create(
                        moet_peso_oppr=int(ordem.orpr_codi),
                        moet_peso_prod=prod_val,
                        moet_peso_codi=prev.orpr_quan_prev or 0,
                        moet_peso_moet=None,
                        moet_peso_sald=prev.orpr_quan_prev or 0,
                    )
                except Exception:
                    continue
        except Exception:
            logger.exception("Falha ao registrar previstos em moveetapeso (OP=%s)", getattr(ordem, "orpr_codi", None))

    @staticmethod
    def registrar_consumo_materia_prima(*, ordem, using, produto_codigo, consumido, usua=0):
        if not OrdemProducaoService.ensure_moveetapeso_table(using=using):
            return None

        produto_codigo_str = str(produto_codigo).strip()
        if not produto_codigo_str:
            return None

        try:
            produto_codigo_int = int(produto_codigo_str)
        except Exception:
            return None

        consumido_val = consumido or 0
        data_mov = ordem.orpr_fech.date() if getattr(ordem, "orpr_fech", None) else timezone.now().date()

        with transaction.atomic(using=using):
            registro = (
                MoveEtapaPeso.objects.using(using)
                .filter(moet_peso_oppr=int(ordem.orpr_codi), moet_peso_prod=int(produto_codigo_int))
                .first()
            )
            if not registro:
                registro = MoveEtapaPeso(moet_peso_oppr=int(ordem.orpr_codi), moet_peso_prod=int(produto_codigo_int))
                registro.moet_peso_codi = 0
                registro.moet_peso_moet = 0
                registro.moet_peso_sald = 0

            usado_antes = registro.moet_peso_moet or 0
            previsto = registro.moet_peso_codi or 0
            delta = consumido_val - usado_antes

            registro.moet_peso_moet = consumido_val
            registro.moet_peso_sald = (previsto or 0) - (consumido_val or 0)
            registro.save(using=using)

            if delta:
                try:
                    from Saidas_Estoque.models import SaidasEstoque

                    said = SaidasEstoque.objects.using(using).filter(
                        said_empr=int(ordem.orpr_empr),
                        said_fili=int(ordem.orpr_fili),
                        said_prod=str(produto_codigo_str)[:10],
                        said_data=data_mov,
                    ).first()

                    if not said:
                        proximo = (SaidasEstoque.objects.using(using).aggregate(Max("said_sequ"))["said_sequ__max"] or 0) + 1
                        if delta > 0:
                            SaidasEstoque.objects.using(using).create(
                                said_sequ=int(proximo),
                                said_empr=int(ordem.orpr_empr),
                                said_fili=int(ordem.orpr_fili),
                                said_prod=str(produto_codigo_str)[:10],
                                said_enti=str(ordem.orpr_clie)[:10] if getattr(ordem, "orpr_clie", None) else None,
                                said_data=data_mov,
                                said_quan=delta,
                                said_tota=0,
                                said_usua=int(usua or 0),
                            )
                    else:
                        novo = (said.said_quan or 0) + delta
                        if novo <= 0:
                            said.delete(using=using)
                        else:
                            said.said_quan = novo
                            said.save(using=using, update_fields=["said_quan"])
                except Exception:
                    pass

                OrdemProducaoService._atualizar_saldo_produto(
                    using=using,
                    empresa=int(ordem.orpr_empr),
                    filial=int(ordem.orpr_fili),
                    produto_codigo=produto_codigo_str,
                    delta=-delta,
                )

            return registro

    @staticmethod
    def dashboard(*, using):
        qs = OrdemProducaoService.listar_ordens(using=using)
        ordens_por_status = {status: qs.filter(orpr_stat=status).count() for status in ["0", "1", "2", "3"]}
        ordens_por_tipo = {tipo: qs.filter(orpr_tipo=tipo).count() for tipo in ["1", "2", "3", "4"]}
        return {
            "total_ordens": qs.count(),
            "ordens_canceladas": qs.filter(orpr_stat='9').count(),
            "ordens_abertas": qs.filter(orpr_stat='0').count(),
            "ordens_producao": qs.filter(orpr_stat='1').count(),
            "ordens_finalizadas": qs.filter(orpr_stat='2').count(),
            "ordens_entregues": qs.filter(orpr_stat='3').count(),
            "ordens_por_status": ordens_por_status, 
            "ordens_por_tipo": ordens_por_tipo,
            "ordens_atrasadas": qs.filter(orpr_prev__lt=timezone.now(), orpr_stat__in=['1', '2']).count(),
        }

    @staticmethod
    def dashboard_detalhado(*, using, filtros=None):
        filtros = filtros or {}
        now = timezone.now()
        qs = OrdemProducaoService.listar_ordens(using=using)

        def _parse_date(v):
            v = (v or "").strip()
            if not v:
                return None
            try:
                return datetime.date.fromisoformat(v)
            except Exception:
                return None

        data_ini = _parse_date(filtros.get("data_ini"))
        data_fim = _parse_date(filtros.get("data_fim"))
        empresa = filtros.get("empr")
        filial = filtros.get("fili")
        tipo = filtros.get("tipo")
        status = filtros.get("status")

        if empresa:
            try:
                qs = qs.filter(orpr_empr=int(empresa))
            except Exception:
                pass
        if filial:
            try:
                qs = qs.filter(orpr_fili=int(filial))
            except Exception:
                pass

        if tipo:
            qs = qs.filter(orpr_tipo=str(tipo))
        if status:
            qs = qs.filter(orpr_stat=str(status))

        if data_ini:
            qs = qs.filter(orpr_entr__date__gte=data_ini)
        if data_fim:
            qs = qs.filter(orpr_entr__date__lte=data_fim)

        total = qs.count()
        kpis = {
            "total": total,
            "abertas": qs.filter(orpr_stat="0").count(),
            "producao": qs.filter(orpr_stat="1").count(),
            "finalizadas": qs.filter(orpr_stat="2").count(),
            "entregues": qs.filter(orpr_stat="3").count(),
            "canceladas": qs.filter(orpr_stat="9").count(),
            "atrasadas": qs.filter(orpr_prev__lt=now, orpr_stat__in=["0", "1"]).count(),
        }

        status_choices = dict(Ordemproducao.status_ordem)
        tipo_choices = dict(Ordemproducao.tipo_ordem)

        status_counts_raw = (
            qs.values("orpr_stat")
            .annotate(total=Count("orpr_codi"))
            .order_by("orpr_stat")
        )
        status_counts = []
        for row in status_counts_raw:
            code = str(row["orpr_stat"])
            status_counts.append({"codigo": code, "label": status_choices.get(code, code), "total": int(row["total"] or 0)})

        tipo_counts_raw = (
            qs.values("orpr_tipo")
            .annotate(total=Count("orpr_codi"))
            .order_by("orpr_tipo")
        )
        tipo_counts = []
        for row in tipo_counts_raw:
            code = str(row["orpr_tipo"])
            tipo_counts.append({"codigo": code, "label": tipo_choices.get(code, code), "total": int(row["total"] or 0)})

        entradas_raw = (
            qs.annotate(d=TruncDate("orpr_entr"))
            .values("d")
            .annotate(total=Count("orpr_codi"))
            .order_by("d")
        )
        finalizadas_qs = OrdemProducaoService.listar_ordens(using=using)
        if empresa:
            try:
                finalizadas_qs = finalizadas_qs.filter(orpr_empr=int(empresa))
            except Exception:
                pass
        if filial:
            try:
                finalizadas_qs = finalizadas_qs.filter(orpr_fili=int(filial))
            except Exception:
                pass
        if tipo:
            finalizadas_qs = finalizadas_qs.filter(orpr_tipo=str(tipo))
        if status:
            finalizadas_qs = finalizadas_qs.filter(orpr_stat=str(status))
        if data_ini:
            finalizadas_qs = finalizadas_qs.filter(orpr_fech__date__gte=data_ini)
        if data_fim:
            finalizadas_qs = finalizadas_qs.filter(orpr_fech__date__lte=data_fim)

        finalizadas_raw = (
            finalizadas_qs.filter(orpr_fech__isnull=False, orpr_stat__in=["2", "3"])
            .annotate(d=TruncDate("orpr_fech"))
            .values("d")
            .annotate(total=Count("orpr_codi"))
            .order_by("d")
        )

        entradas_map = {str(row["d"]): int(row["total"] or 0) for row in entradas_raw if row["d"]}
        finalizadas_map = {str(row["d"]): int(row["total"] or 0) for row in finalizadas_raw if row["d"]}
        dates = sorted(set(list(entradas_map.keys()) + list(finalizadas_map.keys())))
        serie = {
            "labels": dates,
            "entradas": [entradas_map.get(d, 0) for d in dates],
            "finalizadas": [finalizadas_map.get(d, 0) for d in dates],
        }

        return {
            "kpis": kpis,
            "status": status_counts,
            "tipos": tipo_counts,
            "serie": serie,
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
            orpr_empr=ordem.orpr_empr,
            orpr_fili=ordem.orpr_fili,
            orpr_codi=ordem.orpr_codi,
        )

    @staticmethod
    def listar_materiais(*, ordem, using):
        return Ordemprodmate.objects.using(using).filter(orpm_orpr=ordem.orpr_codi)

    @staticmethod
    def listar_etapas(*, ordem, using):
        return Etapa.objects.using(using).all().order_by("etap_nome")

    @staticmethod
    def listar_movimentacoes_etapa(*, ordem, using):
        return (
            Moveetapa.objects.using(using)
            .filter(moet_orpr=ordem)
            .select_related("moet_etap", "moet_ouri")
            .order_by("-moet_codi")
        )

    @staticmethod
    def listar_movimentacoes_saldo(*, ordem, using):
        try:
            table_names = connections[using].introspection.table_names()
            if "moveetapeso" not in table_names:
                return []
        except Exception:
            return []
        return list(MoveEtapaPeso.objects.using(using).filter(moet_peso_oppr=int(ordem.orpr_codi)))

    @staticmethod
    def listar_materiais_previstos(*, ordem, using):
        return (
            Ordemproducaoproduto.objects.using(using)
            .filter(orpr_prod_orpr=ordem)
            .select_related("orpr_prod_prod")
            .order_by("orpr_prod_codi")
        )

    @staticmethod
    def listar_etapas_master(*, using):
        return Etapa.objects.using(using).all().order_by("etap_nome")

    @staticmethod
    def listar_ourives_master(*, using, empresa_id):
        return Ourives.objects.using(using).filter(ouri_empr=int(empresa_id)).order_by("ouri_nome")
