"""Utilitários para lidar com schemas heterogêneos entre bancos de tenant.

Alguns bancos de licenças não possuem todas as colunas declaradas nos models.
Estas funções permitem detectar colunas ausentes e ignorá-las com segurança,
evitando erros de `ProgrammingError` (column does not exist).
"""
from django.db import connections, models


_TABLE_COLUMNS_CACHE = {}


def get_table_columns(*, using: str, table_name: str):
    cache_key = (using or "default", table_name)
    if cache_key in _TABLE_COLUMNS_CACHE:
        return _TABLE_COLUMNS_CACHE[cache_key]
    try:
        connection = connections[using or "default"]
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
        columns = {getattr(col, "name", col[0]) for col in description}
    except Exception:
        columns = set()
    _TABLE_COLUMNS_CACHE[cache_key] = columns
    return columns


def missing_model_field_names_for_db(*, model, using: str):
    table_name = model._meta.db_table
    columns = get_table_columns(using=using, table_name=table_name)
    if not columns:
        return []
    missing = []
    for field in model._meta.concrete_fields:
        try:
            column_name = field.column
        except Exception:
            continue
        if column_name not in columns:
            missing.append(field.name)
    return missing


def campo_existe_no_banco(*, model, field_name: str, using: str) -> bool:
    """Indica se a coluna do campo existe na tabela do banco informado.

    Retorna True quando não for possível introspecionar o schema (assume existência),
    evitando bloquear o fluxo por falha de leitura da tabela.
    """
    try:
        column_name = model._meta.get_field(field_name).column
    except Exception:
        return False
    columns = get_table_columns(using=using, table_name=model._meta.db_table)
    if not columns:
        return True
    return column_name in columns


class SafeMissingColumnsQuerySet(models.QuerySet):
    """QuerySet que ignora colunas ausentes no banco do tenant.

    A verificação é feita em tempo de execução (quando o banco já foi resolvido
    via `.using()`), e não em `get_queryset()` — que roda antes do `.using()`.
    """

    def _missing_field_names(self):
        using = self.db or "default"
        return missing_model_field_names_for_db(model=self.model, using=using)

    def _prepare_missing_columns(self):
        """Remove do SELECT as colunas ausentes e devolve os nomes dos campos."""
        try:
            missing_field_names = self._missing_field_names()
        except Exception:
            return []
        if not missing_field_names:
            return []
        try:
            self.query.add_deferred_loading(missing_field_names)
        except Exception:
            return []
        return missing_field_names

    def _blank_missing_fields(self, instance, missing_field_names):
        """Marca os campos ausentes como já carregados (None/default).

        Sem isso, o acesso ao atributo (ex.: em template) dispararia um
        `refresh_from_db` que reconsultaria a coluna inexistente.
        """
        for field_name in missing_field_names:
            try:
                field = self.model._meta.get_field(field_name)
            except Exception:
                continue
            instance.__dict__[field_name] = None if field.null else field.get_default()

    def _fetch_all(self):
        missing_field_names = []
        if self._result_cache is None:
            missing_field_names = self._prepare_missing_columns()
        result = super()._fetch_all()
        if missing_field_names:
            for obj in self._result_cache or []:
                if isinstance(obj, models.Model):
                    self._blank_missing_fields(obj, missing_field_names)
        return result

    def iterator(self, *args, **kwargs):
        missing_field_names = self._prepare_missing_columns()
        for obj in super().iterator(*args, **kwargs):
            if missing_field_names and isinstance(obj, models.Model):
                self._blank_missing_fields(obj, missing_field_names)
            yield obj


class SafeMissingColumnsManager(models.Manager.from_queryset(SafeMissingColumnsQuerySet)):
    pass
