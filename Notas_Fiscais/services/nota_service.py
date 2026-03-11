# notas_fiscais/services/nota_service.py

from django.db import IntegrityError, transaction
from django.db.models import Max
import logging

logger = logging.getLogger(__name__)

from django.core.exceptions import ValidationError
from Licencas.models import Filiais
from Entidades.models import Entidades
from ..models import Nota, NotaItem
from ..handlers.nota_handler import NotaHandler
from .itens_service import ItensService
from .transporte_service import TransporteService
from .evento_service import EventoService
from .calculo_impostos_service import CalculoImpostosService
from series.models import Series


class NotaService:

    @staticmethod
    def criar(data, itens, impostos_map, transporte, empresa, filial, database="default"):
        with transaction.atomic(using=database):
            dest_id = data.get("destinatario")
            try:
                destinatario = Entidades.objects.using(database).get(enti_clie=dest_id)
            except Entidades.DoesNotExist:
                raise ValidationError("Destinatário inválido.")

            emitente = Filiais.objects.using(database).get(empr_empr=empresa, empr_codi=filial)

            series = (
                Series.objects.using(database)
                .filter(seri_empr=empresa, seri_fili=filial, seri_nome="SA")
                .first()
            )
            if not series:
                raise ValidationError("Nenhuma série encontrada para o modelo 55.")

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
    @transaction.atomic
    def atualizar(nota, data, itens, impostos_map, transporte, database="default"):

        dest_id = data.get("destinatario")

        try:
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
        nota.save()

        # Itens
        ItensService.atualizar_itens(nota, itens, impostos_map)

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
