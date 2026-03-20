# notas_fiscais/services/nota_service.py

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

logger = logging.getLogger(__name__)

from django.core.exceptions import ValidationError
from django.utils import timezone
from Licencas.models import Filiais
from Entidades.models import Entidades
from ..models import Nota, NotaItem
from ..handlers.nota_handler import NotaHandler
from .itens_service import ItensService
from .transporte_service import TransporteService
from .evento_service import EventoService
from .calculo_impostos_service import CalculoImpostosService
from series.models import Series
from Produtos.models import SaldoProduto
from Entradas_Estoque.models import EntradaEstoque
from Saidas_Estoque.models import SaidasEstoque


class NotaService:
    @staticmethod
    def _to_qty(valor) -> Decimal:
        try:
            return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")

    @staticmethod
    def _to_money(valor) -> Decimal:
        try:
            return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception:
            return Decimal("0.00")

    @staticmethod
    def _itens_por_produto(*, itens_qs) -> dict:
        agg = {}
        for it in itens_qs:
            prod = getattr(it, "produto_id", None)
            prod = str(prod or "").strip()
            if not prod:
                continue
            q = NotaService._to_qty(getattr(it, "quantidade", None))
            unit = Decimal(str(getattr(it, "unitario", None) or 0))
            desc = Decimal(str(getattr(it, "desconto", None) or 0))
            total = NotaService._to_money((q * unit) - desc)
            atual = agg.get(prod) or {"q": Decimal("0.00"), "t": Decimal("0.00")}
            atual["q"] = NotaService._to_qty(atual["q"] + q)
            atual["t"] = NotaService._to_money(atual["t"] + total)
            agg[prod] = atual
        return agg

    @staticmethod
    def _obter_saldo_produto(*, produto: str, empresa: int, filial: int, database: str) -> Decimal:
        sp = (
            SaldoProduto.objects.using(database)
            .filter(produto_codigo_id=str(produto), empresa=str(empresa), filial=str(filial))
            .first()
        )
        if sp is not None:
            try:
                return Decimal(str(getattr(sp, "saldo_estoque", 0) or 0))
            except Exception:
                return Decimal("0")

        total_entradas = (
            EntradaEstoque.objects.using(database)
            .filter(entr_empr=int(empresa), entr_fili=int(filial), entr_prod=str(produto))
            .aggregate(total=Sum("entr_quan"))
            .get("total")
            or 0
        )
        total_saidas = (
            SaidasEstoque.objects.using(database)
            .filter(said_empr=int(empresa), said_fili=int(filial), said_prod=str(produto))
            .aggregate(total=Sum("said_quan"))
            .get("total")
            or 0
        )
        return Decimal(str(total_entradas or 0)) - Decimal(str(total_saidas or 0))

    @staticmethod
    def _validar_delta_estoque(*, empresa: int, filial: int, database: str, delta_impact_por_prod: dict):
        for prod, delta_impact in (delta_impact_por_prod or {}).items():
            delta = Decimal(str(delta_impact or 0))
            if delta >= 0:
                continue
            saldo = NotaService._obter_saldo_produto(produto=str(prod), empresa=empresa, filial=filial, database=database)
            if saldo < (-delta):
                raise ValidationError(
                    f"Estoque insuficiente para ajustar devolução do produto {prod}. "
                    f"Saldo: {saldo} / Necessário: {-delta}."
                )

    @staticmethod
    def _ajustar_saida(
        *,
        empresa: int,
        filial: int,
        produto: str,
        data_mov: date,
        delta_q: Decimal,
        delta_t: Decimal,
        entidade_id: int,
        usuario_id: int,
        database: str,
    ):
        delta_q = NotaService._to_qty(delta_q)
        delta_t = NotaService._to_money(delta_t)
        if delta_q == 0 and delta_t == 0:
            return

        rec = (
            SaidasEstoque.objects.using(database)
            .filter(said_empr=int(empresa), said_fili=int(filial), said_prod=str(produto), said_data=data_mov)
            .first()
        )
        if rec is None:
            if delta_q < 0:
                raise ValidationError("Movimentação de estoque inválida: tentativa de reduzir saída inexistente.")
            seq = int(SaidasEstoque.objects.using(database).aggregate(max_sequ=Max("said_sequ")).get("max_sequ") or 0) + 1
            SaidasEstoque.objects.using(database).create(
                said_sequ=seq,
                said_empr=int(empresa),
                said_fili=int(filial),
                said_prod=str(produto),
                said_enti=str(entidade_id or ""),
                said_data=data_mov,
                said_quan=delta_q,
                said_tota=delta_t,
                said_obse="Devolução",
                said_usua=int(usuario_id or 1),
            )
            return

        novo_q = NotaService._to_qty(Decimal(str(rec.said_quan or 0)) + delta_q)
        novo_t = NotaService._to_money(Decimal(str(rec.said_tota or 0)) + delta_t)
        if novo_q < 0:
            raise ValidationError("Movimentação de estoque inválida: saída ficaria negativa.")
        if novo_q == 0:
            rec.delete(using=database)
            return
        rec.said_quan = novo_q
        rec.said_tota = novo_t
        if not rec.said_enti and entidade_id:
            rec.said_enti = str(entidade_id)
        if not rec.said_obse:
            rec.said_obse = "Devolução"
        if usuario_id:
            rec.said_usua = int(usuario_id)
        rec.save(using=database)

    @staticmethod
    def _ajustar_entrada(
        *,
        empresa: int,
        filial: int,
        produto: str,
        data_mov: date,
        delta_q: Decimal,
        delta_t: Decimal,
        entidade_id: int,
        usuario_id: int,
        database: str,
    ):
        delta_q = NotaService._to_qty(delta_q)
        delta_t = NotaService._to_money(delta_t)
        if delta_q == 0 and delta_t == 0:
            return

        rec = (
            EntradaEstoque.objects.using(database)
            .filter(entr_empr=int(empresa), entr_fili=int(filial), entr_prod=str(produto), entr_data=data_mov)
            .first()
        )
        if rec is None:
            if delta_q < 0:
                raise ValidationError("Movimentação de estoque inválida: tentativa de reduzir entrada inexistente.")
            seq = int(EntradaEstoque.objects.using(database).aggregate(max_sequ=Max("entr_sequ")).get("max_sequ") or 0) + 1
            EntradaEstoque.objects.using(database).create(
                entr_sequ=seq,
                entr_empr=int(empresa),
                entr_fili=int(filial),
                entr_prod=str(produto),
                entr_enti=str(entidade_id or ""),
                entr_data=data_mov,
                entr_quan=delta_q,
                entr_tota=delta_t,
                entr_obse="Devolução",
                entr_usua=int(usuario_id or 1),
            )
            return

        novo_q = NotaService._to_qty(Decimal(str(rec.entr_quan or 0)) + delta_q)
        novo_t = NotaService._to_money(Decimal(str(rec.entr_tota or 0)) + delta_t)
        if novo_q < 0:
            raise ValidationError("Movimentação de estoque inválida: entrada ficaria negativa.")
        if novo_q == 0:
            rec.delete(using=database)
            return
        rec.entr_quan = novo_q
        rec.entr_tota = novo_t
        if not rec.entr_enti and entidade_id:
            rec.entr_enti = str(entidade_id)
        if not rec.entr_obse:
            rec.entr_obse = "Devolução"
        if usuario_id:
            rec.entr_usua = int(usuario_id)
        rec.save(using=database)

    @staticmethod
    def criar(data, itens, impostos_map, transporte, empresa, filial, database="default"):
        with transaction.atomic(using=database):
            dest_id = data.get("destinatario")
            try:
                if isinstance(dest_id, Entidades):
                    destinatario = dest_id
                else:
                    destinatario = Entidades.objects.using(database).get(enti_clie=dest_id)
            except Entidades.DoesNotExist:
                raise ValidationError("Destinatário inválido.")

            emitente = Filiais.objects.using(database).get(empr_empr=empresa, empr_codi=filial)

            modelo_in = str(data.get("modelo") or "55").strip()
            try:
                regime_emitente = str(getattr(emitente, "empr_regi_trib", "") or "").strip()
            except Exception:
                regime_emitente = ""
            is_produtor_rural = regime_emitente == "5"
            if is_produtor_rural:
                serie_tipos = ["PR"]
            elif modelo_in == "65":
                serie_tipos = ["NC"]
            else:
                serie_tipos = ["SA"]

            serie_in = str(data.get("serie") or "").strip()
            serie_candidates = []
            if serie_in:
                serie_candidates.append(serie_in)
                if serie_in.isdigit():
                    serie_candidates.append(serie_in.zfill(3))
            serie_candidates = [s for s in serie_candidates if s]
            serie_candidates = list(dict.fromkeys(serie_candidates))

            series = None
            if serie_candidates:
                qs_series = Series.objects.using(database).filter(
                    seri_empr=empresa,
                    seri_fili=filial,
                    seri_nome__in=serie_tipos,
                    seri_codi__in=serie_candidates,
                )
                if is_produtor_rural:
                    qs_series = qs_series.filter(seri_codi__gte="920", seri_codi__lte="969")
                series = qs_series.first()
                if not series:
                    if serie_in in ("1", "001"):
                        qs_series = Series.objects.using(database).filter(
                            seri_empr=empresa,
                            seri_fili=filial,
                            seri_nome__in=serie_tipos,
                        )
                        if is_produtor_rural:
                            qs_series = qs_series.filter(seri_codi__gte="920", seri_codi__lte="969")
                        series = qs_series.first()
                    if not series:
                        raise ValidationError("Série inválida para Nota de Saída.")
            else:
                qs_series = Series.objects.using(database).filter(
                    seri_empr=empresa,
                    seri_fili=filial,
                    seri_nome__in=serie_tipos,
                )
                if is_produtor_rural:
                    qs_series = qs_series.filter(seri_codi__gte="920", seri_codi__lte="969")
                series = qs_series.first()
                if not series:
                    raise ValidationError("Nenhuma série cadastrada para Nota de Saída.")

            serie_saida = str(getattr(series, "seri_codi", None) or "1").strip()

            payload = NotaHandler.preparar_criacao(data, empresa, filial)
            payload["emitente"] = emitente
            payload["destinatario"] = destinatario
            payload["ambiente"] = int(emitente.empr_ambi_nfe or 2)

            modelo = str(payload.get("modelo") or "55").strip()
            payload["modelo"] = modelo

            serie = str(serie_saida or "1").strip()
            payload["serie"] = serie

            numero = int(payload.get("numero") or 0)
            if numero > 0:
                existe = (
                    Nota.objects.using(database)
                    .filter(
                        empresa=empresa,
                        filial=filial,
                        modelo=modelo,
                        serie=serie,
                        numero=numero,
                    )
                    .exists()
                )
                if existe:
                    numero = 0

            if numero <= 0:
                payload["numero"] = NotaService.next_numero(empresa, filial, modelo, serie, database)

            nota = None
            for _ in range(5):
                try:
                    nota = Nota.objects.using(database).create(**payload)
                    break
                except IntegrityError as e:
                    msg = str(e).lower()
                    if ("duplicate key" not in msg) and ("unique" not in msg):
                        raise
                    payload["numero"] = NotaService.next_numero(empresa, filial, modelo, serie, database)

            if nota is None:
                raise ValidationError("Não foi possível obter numeração disponível para a nota.")

            logger.info(
                "Nota criada id=%s empresa=%s filial=%s modelo=%s serie=%s numero=%s",
                getattr(nota, "pk", None),
                empresa,
                filial,
                modelo,
                serie,
                payload.get("numero"),
            )

            ItensService.inserir_itens(nota, itens, impostos_map)

            if transporte:
                TransporteService.definir(nota, transporte)

            return nota

    @staticmethod
    def next_numero(empresa: int, filial: int, modelo: str, serie: str, database: str = "default") -> int:
        qs = Nota.objects.using(database).filter(
            empresa=empresa, filial=filial, modelo=str(modelo).strip(), serie=str(serie).strip()
        )
        max_num = qs.aggregate(max_num=Max("numero")).get("max_num") or 0
        return int(max_num) + 1

    @staticmethod
    def atualizar(nota, data, itens, impostos_map, transporte, database="default", usuario_id=None):
        with transaction.atomic(using=database):
            empresa = int(getattr(nota, "empresa", 0) or 0)
            filial = int(getattr(nota, "filial", 0) or 0)
            entidade_id = int(getattr(nota, "destinatario_id", 0) or 0)
            usuario_mov = int(usuario_id or 1)

            old_finalidade = int(getattr(nota, "finalidade", 0) or 0)
            old_tipo = int(getattr(nota, "tipo_operacao", 0) or 0)
            old_data_emissao = getattr(nota, "data_emissao", None) or timezone.now().date()
            if not isinstance(old_data_emissao, date):
                old_data_emissao = timezone.now().date()
            old_itens_qs = NotaItem.objects.using(database).filter(nota=nota)
            old_map = NotaService._itens_por_produto(itens_qs=old_itens_qs)

            dest_id = data.get("destinatario")

            try:
                if isinstance(dest_id, Entidades):
                    destinatario = dest_id
                else:
                    destinatario = Entidades.objects.using(database).get(enti_clie=dest_id)
            except Entidades.DoesNotExist:
                raise ValidationError("Destinatário inválido.")

            # Atualiza apenas campos editáveis
            campos_editaveis = [
                "modelo", "serie", "numero",
                "data_emissao", "data_saida",
                "tipo_operacao", "finalidade",
            ]

            for campo in campos_editaveis:
                if campo in data:
                    setattr(nota, campo, data[campo])

            nota.destinatario = destinatario
            nota.save(using=database)

            # Itens
            ItensService.atualizar_itens(nota, itens, impostos_map)
            new_itens_qs = NotaItem.objects.using(database).filter(nota=nota)
            new_map = NotaService._itens_por_produto(itens_qs=new_itens_qs)

            new_finalidade = int(getattr(nota, "finalidade", 0) or 0)
            new_tipo = int(getattr(nota, "tipo_operacao", 0) or 0)
            new_data_emissao = getattr(nota, "data_emissao", None) or timezone.now().date()
            if not isinstance(new_data_emissao, date):
                new_data_emissao = timezone.now().date()

            if old_finalidade == 4 or new_finalidade == 4:
                delta_impact = {}
                for prod, vals in old_map.items():
                    q_old = NotaService._to_qty(vals.get("q"))
                    if old_finalidade == 4:
                        old_imp = q_old if old_tipo == 0 else -q_old
                        delta_impact[prod] = delta_impact.get(prod, Decimal("0")) - old_imp
                for prod, vals in new_map.items():
                    q_new = NotaService._to_qty(vals.get("q"))
                    if new_finalidade == 4:
                        new_imp = q_new if new_tipo == 0 else -q_new
                        delta_impact[prod] = delta_impact.get(prod, Decimal("0")) + new_imp
                NotaService._validar_delta_estoque(
                    empresa=empresa,
                    filial=filial,
                    database=database,
                    delta_impact_por_prod=delta_impact,
                )

                if old_finalidade == 4:
                    for prod, vals in old_map.items():
                        dq = NotaService._to_qty(vals.get("q"))
                        dt = NotaService._to_money(vals.get("t"))
                        if old_tipo == 1:
                            NotaService._ajustar_saida(
                                empresa=empresa,
                                filial=filial,
                                produto=str(prod),
                                data_mov=old_data_emissao,
                                delta_q=-dq,
                                delta_t=-dt,
                                entidade_id=entidade_id,
                                usuario_id=usuario_mov,
                                database=database,
                            )
                        else:
                            NotaService._ajustar_entrada(
                                empresa=empresa,
                                filial=filial,
                                produto=str(prod),
                                data_mov=old_data_emissao,
                                delta_q=-dq,
                                delta_t=-dt,
                                entidade_id=entidade_id,
                                usuario_id=usuario_mov,
                                database=database,
                            )

                if new_finalidade == 4:
                    for prod, vals in new_map.items():
                        dq = NotaService._to_qty(vals.get("q"))
                        dt = NotaService._to_money(vals.get("t"))
                        if new_tipo == 1:
                            NotaService._ajustar_saida(
                                empresa=empresa,
                                filial=filial,
                                produto=str(prod),
                                data_mov=new_data_emissao,
                                delta_q=dq,
                                delta_t=dt,
                                entidade_id=entidade_id,
                                usuario_id=usuario_mov,
                                database=database,
                            )
                        else:
                            NotaService._ajustar_entrada(
                                empresa=empresa,
                                filial=filial,
                                produto=str(prod),
                                data_mov=new_data_emissao,
                                delta_q=dq,
                                delta_t=dt,
                                entidade_id=entidade_id,
                                usuario_id=usuario_mov,
                                database=database,
                            )

            # Calcular Impostos
            if not impostos_map:
                CalculoImpostosService(database).aplicar_impostos(nota)

            # Transporte
            if transporte:
                TransporteService.definir(nota, transporte)

            return nota

    @staticmethod
    @transaction.atomic
    def cancelar(nota, descricao, xml=None, protocolo=None, database="default"):
        if nota.status == 101:
            raise ValidationError("Nota já cancelada.")

        EventoService.registrar(
            nota=nota,
            tipo="cancelamento",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
            using=database
        )

        nota.status = 101
        nota.save(using=database, update_fields=["status"])
        return nota
    
    @staticmethod
    def atualizar_totais(nota: Nota):
        """Recalcula totais da nota após cálculo de impostos"""
        db_alias = getattr(getattr(nota, "_state", None), "db", None) or "default"
        itens = NotaItem.objects.using(db_alias).filter(nota=nota).select_related("impostos")
        
        total_produtos = sum(
            (item.total_item if item.total_item is not None else (item.quantidade * item.unitario - (item.desconto or 0)))
            for item in itens
        )
        
        total_tributos = sum(
            (getattr(getattr(item, "impostos", None), "icms_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "icms_st_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "ipi_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "pis_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "cofins_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "cbs_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "ibs_valor", None) or 0) +
            (getattr(getattr(item, "impostos", None), "fcp_valor", None) or 0)
            for item in itens
        )
        
        nota.total = total_produtos + total_tributos
        nota.save(using=db_alias, update_fields=["total"])
        return nota

    @staticmethod
    @transaction.atomic
    def transmitir(nota, descricao="Transmitida via painel", chave=None, protocolo=None, xml=None, database="default"):
        if nota.status == 100:
            raise ValidationError("Nota já autorizada.")

        EventoService.registrar(
            nota=nota,
            tipo="autorizacao",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
            using=database
        )

        if chave:
            nota.chave_acesso = chave
        if protocolo:
            nota.protocolo_autorizacao = protocolo
        if xml:
            nota.xml_autorizado = xml

        nota.status = 100
        nota.save(using=database, update_fields=["status", "chave_acesso", "protocolo_autorizacao", "xml_autorizado"])
        return nota

    @staticmethod
    @transaction.atomic
    def gravar(nota, descricao="Rascunho criado", database="default"):
        if nota.status != 0:
            nota.status = 0
            nota.save(using=database, update_fields=["status"])
        EventoService.registrar(
            nota=nota,
            tipo="rascunho",
            descricao=descricao,
            using=database
        )
        return nota

    @staticmethod
    @transaction.atomic
    def inutilizar(nota, descricao, xml=None, protocolo=None, database="default"):
        if nota.status == 102:
            raise ValidationError("Nota já inutilizada.")

        EventoService.registrar(
            nota=nota,
            tipo="inutilizacao",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
            using=database
        )

        nota.status = 102
        nota.save(using=database, update_fields=["status"])
        return nota
