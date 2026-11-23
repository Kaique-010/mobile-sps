
"""
Utilitários para lidar com schemas heterogêneos entre bancos de tenant.

Permite ignorar colunas ausentes em operações de leitura e escrita,
evitando ProgrammingError quando os bancos possuem estruturas diferentes.
"""

import logging
from threading import RLock

from django.db import connections, models, transaction


logger = logging.getLogger(__name__)

_TABLE_COLUMNS_CACHE = {}
_TABLE_COLUMNS_LOCK = RLock()


def invalidar_cache_colunas(*, using=None, table_name=None):
    """
    Invalida o cache de introspecção.

    Exemplos:
        invalidar_cache_colunas()
        invalidar_cache_colunas(using="default")
        invalidar_cache_colunas(using="default", table_name="entidades")
    """
    with _TABLE_COLUMNS_LOCK:
        if using is None and table_name is None:
            _TABLE_COLUMNS_CACHE.clear()
            return

        keys = list(_TABLE_COLUMNS_CACHE.keys())

        for key in keys:
            db_alias, cached_table = key

            if using is not None and db_alias != using:
                continue

            if table_name is not None and cached_table != table_name:
                continue

            _TABLE_COLUMNS_CACHE.pop(key, None)


def get_table_columns(*, using: str, table_name: str):
    using = using or "default"
    cache_key = (using, table_name)

    with _TABLE_COLUMNS_LOCK:
        if cache_key in _TABLE_COLUMNS_CACHE:
            return _TABLE_COLUMNS_CACHE[cache_key]

    try:
        connection = connections[using]

        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                table_name
            )

        columns = {
            col.name if hasattr(col, "name") else col[0]
            for col in description
        }

    except Exception:
        logger.exception(
            "[SAFE DB] Erro ao identificar colunas: banco=%s tabela=%s",
            using,
            table_name
        )

        # Falha aberta: não modifica o comportamento original do ORM.
        columns = set()

    with _TABLE_COLUMNS_LOCK:
        _TABLE_COLUMNS_CACHE[cache_key] = columns

    return columns


def missing_model_field_names_for_db(*, model, using: str):
    columns = get_table_columns(
        using=using,
        table_name=model._meta.db_table
    )

    # Introspecção indisponível: mantém comportamento original.
    if not columns:
        return []

    missing = []

    for field in model._meta.concrete_fields:
        if field.column not in columns:
            missing.append(field.name)

    return missing


def campo_existe_no_banco(*, model, field_name: str, using: str) -> bool:
    try:
        field = model._meta.get_field(field_name)
    except Exception:
        field = next(
            (
                f for f in model._meta.concrete_fields
                if f.attname == field_name
            ),
            None
        )

    if field is None:
        return False

    columns = get_table_columns(
        using=using,
        table_name=model._meta.db_table
    )

    # Não bloqueia operações se a introspecção falhar.
    if not columns:
        return True

    return field.column in columns


def _get_field_for_write(model, field_name):
    """
    Resolve campos normais e ForeignKeys pelo nome ou attname.
    """
    try:
        return model._meta.get_field(field_name)
    except Exception:
        return next(
            (
                field
                for field in model._meta.concrete_fields
                if field.attname == field_name
            ),
            None
        )


class SafeMissingColumnsQuerySet(models.QuerySet):

    # =====================================================
    # INFRAESTRUTURA
    # =====================================================

    def _missing_field_names(self):
        using = self.db or "default"

        return missing_model_field_names_for_db(
            model=self.model,
            using=using
        )

    def _get_existing_fields(self):
        """
        Retorna somente os campos concretos existentes no banco.
        """
        columns = get_table_columns(
            using=self.db or "default",
            table_name=self.model._meta.db_table
        )

        # Se não conseguimos inspecionar, preservamos o ORM original.
        if not columns:
            return list(self.model._meta.concrete_fields)

        return [
            field
            for field in self.model._meta.concrete_fields
            if field.column in columns
        ]

    def _field_exists_for_write(self, field_name):
        field = _get_field_for_write(self.model, field_name)

        if field is None:
            return True

        columns = get_table_columns(
            using=self.db or "default",
            table_name=self.model._meta.db_table
        )

        if not columns:
            return True

        return field.column in columns

    # =====================================================
    # LEITURA SEGURA
    # =====================================================

    def _prepare_missing_columns(self):
        try:
            missing_field_names = self._missing_field_names()
        except Exception:
            logger.exception(
                "[SAFE DB] Erro preparando SELECT de %s",
                self.model.__name__
            )
            return []

        if not missing_field_names:
            return []

        try:
            self.query.add_deferred_loading(missing_field_names)
        except Exception:
            logger.exception(
                "[SAFE DB] Erro ao deferir campos de %s",
                self.model.__name__
            )
            return []

        return missing_field_names

    def _blank_missing_fields(self, instance, missing_field_names):
        """
        Marca campos ausentes como carregados para evitar refresh_from_db.
        """
        for field_name in missing_field_names:
            try:
                field = self.model._meta.get_field(field_name)
            except Exception:
                continue

            value = None if field.null else field.get_default()

            instance.__dict__[field.attname] = value

    def _fetch_all(self):
        missing_field_names = []

        if self._result_cache is None:
            missing_field_names = self._prepare_missing_columns()

        result = super()._fetch_all()

        if missing_field_names:
            for obj in self._result_cache or []:
                if isinstance(obj, models.Model):
                    self._blank_missing_fields(
                        obj,
                        missing_field_names
                    )

        return result

    def iterator(self, *args, **kwargs):
        missing_field_names = self._prepare_missing_columns()

        for obj in super().iterator(*args, **kwargs):
            if missing_field_names and isinstance(obj, models.Model):
                self._blank_missing_fields(
                    obj,
                    missing_field_names
                )

            yield obj

    # =====================================================
    # INSERT SEGURO
    # =====================================================

    def _safe_insert_instance(self, obj):
        """
        Insere uma instância utilizando somente colunas existentes.

        Utiliza a operação interna de INSERT do QuerySet para evitar
        que Model.save() tente inserir todas as colunas do model.
        """
        fields = self._get_existing_fields()

        # AutoField é gerado pelo banco quando não existe PK informado.
        if obj.pk is None:
            fields = [
                field
                for field in fields
                if not (
                    field.primary_key
                    and field.auto_created
                )
            ]

        if not fields:
            raise RuntimeError(
                "Nenhuma coluna disponível para inserir "
                f"o model {self.model.__name__}."
            )

        pk_field = self.model._meta.pk

        return_id = (
            pk_field.auto_created
            and obj.pk is None
        )

        inserted_id = self._insert(
            [obj],
            fields=fields,
            return_id=return_id,
            using=self.db
        )

        if return_id and inserted_id is not None:
            obj.pk = inserted_id

        obj._state.adding = False
        obj._state.db = self.db

        return obj

    def create(self, **kwargs):
        """
        Cria uma instância ignorando campos que não existem na tabela.
        """
        safe_kwargs = {
            key: value
            for key, value in kwargs.items()
            if self._field_exists_for_write(key)
        }

        ignored = set(kwargs) - set(safe_kwargs)

        if ignored:
            logger.warning(
                "[SAFE DB] INSERT %s: campos ignorados: %s",
                self.model.__name__,
                sorted(ignored)
            )

        obj = self.model(**safe_kwargs)

        with transaction.atomic(using=self.db):
            self._safe_insert_instance(obj)

        return obj

    # =====================================================
    # UPDATE SEGURO
    # =====================================================

    def update(self, **kwargs):
        """
        Atualiza somente campos existentes na tabela.
        """
        safe_kwargs = {
            key: value
            for key, value in kwargs.items()
            if self._field_exists_for_write(key)
        }

        ignored = set(kwargs) - set(safe_kwargs)

        if ignored:
            logger.warning(
                "[SAFE DB] UPDATE %s: campos ignorados: %s",
                self.model.__name__,
                sorted(ignored)
            )

        if not safe_kwargs:
            return 0

        return super().update(**safe_kwargs)

    # =====================================================
    # BULK CREATE SEGURO
    # =====================================================

    def bulk_create(self, objs, batch_size=None):
        """
        Insere objetos individualmente utilizando somente colunas existentes.

        Mantém a segurança em schemas heterogêneos. Esta implementação
        prioriza compatibilidade, não desempenho de inserção em lote.
        """
        objs = list(objs)

        if not objs:
            return objs

        with transaction.atomic(using=self.db):
            for obj in objs:
                if not isinstance(obj, self.model):
                    raise TypeError(
                        f"Esperado {self.model.__name__}, "
                        f"recebido {type(obj).__name__}"
                    )

                self._safe_insert_instance(obj)

        return objs


class SafeMissingColumnsManager(
    models.Manager.from_queryset(SafeMissingColumnsQuerySet)
):
    pass
