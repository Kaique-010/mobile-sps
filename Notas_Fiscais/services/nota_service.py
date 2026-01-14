# notas_fiscais/services/nota_service.py

from django.db import transaction
from django.core.exceptions import ValidationError
from Licencas.models import Filiais
from Entidades.models import Entidades
from ..models import Nota
from ..handlers.nota_handler import NotaHandler
from .itens_service import ItensService
from .transporte_service import TransporteService
from .evento_service import EventoService


class NotaService:

    @staticmethod
    @transaction.atomic
    def criar(data, itens, impostos_map, transporte, empresa, filial, database="default"):

        # 1. Validar destinatário existe
        dest_id = data.get("destinatario")
        try:
            destinatario = Entidades.objects.using(database).get(enti_clie=dest_id)
        except Entidades.DoesNotExist:
            raise ValidationError("Destinatário inválido.")

        # 2. Emitente = filial específica (empresa + filial)
        emitente = Filiais.objects.using(database).get(empr_empr=empresa, empr_codi=filial)

        # 3. Prepara payload
        payload = NotaHandler.preparar_criacao(data, empresa, filial)
        payload["emitente"] = emitente
        payload["destinatario"] = destinatario

        # 3.1. Número automático
        modelo = str(payload.get("modelo") or "55")
        serie = str(payload.get("serie") or "1")
        numero = int(payload.get("numero") or 0)
        if numero <= 0:
            numero = NotaService.next_numero(empresa, filial, modelo, serie, database)
            payload["numero"] = numero
        else:
            exists = (
                Nota.objects.using(database)
                .filter(empresa=empresa, filial=filial, modelo=modelo, serie=serie, numero=numero)
                .exists()
            )
            if exists:
                numero = NotaService.next_numero(empresa, filial, modelo, serie, database)
                payload["numero"] = numero

        # 4. Cria a nota
        nota = Nota.objects.using(database).create(**payload)

        # 5. Itens
        ItensService.inserir_itens(nota, itens, impostos_map)

        # 6. Transporte
        if transporte:
            TransporteService.definir(nota, transporte)

        return nota

    @staticmethod
    def next_numero(empresa: int, filial: int, modelo: str, serie: str, database: str = "default") -> int:
        qs = (
            Nota.objects.using(database)
            .filter(empresa=empresa, filial=filial, modelo=modelo, serie=serie)
        )
        last_aut = qs.filter(status=100).order_by("-numero").values_list("numero", flat=True).first()
        if last_aut:
            return int(last_aut) + 1
        last_any = qs.order_by("-numero").values_list("numero", flat=True).first()
        if last_any:
            return int(last_any) + 1
        return 1

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
    def cancelar(nota, descricao, xml=None, protocolo=None):
        if nota.status == 101:
            raise ValidationError("Nota já cancelada.")

        EventoService.registrar(
            nota=nota,
            tipo="cancelamento",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        nota.status = 101
        nota.save(update_fields=["status"])
        return nota

    @staticmethod
    @transaction.atomic
    def transmitir(nota, descricao="Transmitida via painel", chave=None, protocolo=None, xml=None):
        if nota.status == 100:
            raise ValidationError("Nota já autorizada.")

        EventoService.registrar(
            nota=nota,
            tipo="autorizacao",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        if chave:
            nota.chave_acesso = chave
        if protocolo:
            nota.protocolo_autorizacao = protocolo
        if xml:
            nota.xml_autorizado = xml

        nota.status = 100
        nota.save(update_fields=["status", "chave_acesso", "protocolo_autorizacao", "xml_autorizado"])
        return nota

    @staticmethod
    @transaction.atomic
    def gravar(nota, descricao="Rascunho criado"):
        if nota.status != 0:
            nota.status = 0
            nota.save(update_fields=["status"])
        EventoService.registrar(
            nota=nota,
            tipo="rascunho",
            descricao=descricao,
        )
        return nota

    @staticmethod
    @transaction.atomic
    def inutilizar(nota, descricao, xml=None, protocolo=None):
        if nota.status == 102:
            raise ValidationError("Nota já inutilizada.")

        EventoService.registrar(
            nota=nota,
            tipo="inutilizacao",
            descricao=descricao,
            xml=xml,
            protocolo=protocolo,
        )

        nota.status = 102
        nota.save(update_fields=["status"])
        return nota
