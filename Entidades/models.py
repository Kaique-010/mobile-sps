from django.db import connections, models
from django.db.utils import OperationalError, ProgrammingError
import logging

logger = logging.getLogger(__name__)


_TABLE_COLUMNS_CACHE = {}


def _get_table_columns(*, using: str, table_name: str):
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


def _missing_model_field_names_for_db(*, model, using: str):
    table_name = model._meta.db_table
    columns = _get_table_columns(using=using, table_name=table_name)
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


class SafeMissingColumnsQuerySet(models.QuerySet):
    def _apply_missing_columns_deferral(self):
        using = self.db or "default"
        missing_field_names = _missing_model_field_names_for_db(model=self.model, using=using)
        if missing_field_names:
            return self.defer(*missing_field_names)
        return self

    def iterator(self, *args, **kwargs):
        try:
            return super(SafeMissingColumnsQuerySet, self._apply_missing_columns_deferral()).iterator(*args, **kwargs)
        except (ProgrammingError, OperationalError):
            return super().iterator(*args, **kwargs)


class SafeMissingColumnsManager(models.Manager.from_queryset(SafeMissingColumnsQuerySet)):
    def get_queryset(self):
        qs = super().get_queryset()
        try:
            return qs._apply_missing_columns_deferral()
        except Exception:
            return qs


class Entidades(models.Model):
    TIPO_ENTIDADES = [
        ('FO', 'FORNECEDOR'),
        ('CL', 'CLIENTE'),
        ('AM', 'AMBOS'),
        ('OU', 'OUTROS'),
        ('VE', 'VENDEDOR'),
        ('FU', 'FUNCIONÁRIOS'),
    ]

    enti_empr = models.IntegerField()
    enti_clie = models.BigIntegerField(unique=True, primary_key=True)
    enti_nome = models.CharField(max_length=100, default='')
    enti_tipo_enti = models.CharField(max_length=100, choices=TIPO_ENTIDADES, default='FO')
    enti_fant = models.CharField(max_length=100, default='', blank=True, null=True)  
    enti_cpf = models.CharField(max_length=11, blank=True, null=True)  
    enti_cnpj = models.CharField(max_length=14, blank=True, null=True)  
    enti_insc_esta = models.CharField(max_length=14, blank=True, null=True)    
    enti_cep = models.CharField(max_length=8) 
    enti_ende = models.CharField(max_length=60)
    enti_nume = models.CharField(max_length=10)  
    enti_cida = models.CharField(max_length=60)
    enti_esta = models.CharField(max_length=2)
    enti_pais = models.CharField(max_length=60, default='1058')
    enti_codi_pais = models.CharField(max_length=6, default='1058')
    enti_codi_cida = models.CharField(max_length=7, default='0000000')
    enti_bair = models.CharField(max_length=60)
    enti_comp = models.CharField(max_length=60, blank=True, null=True)
    enti_fone = models.CharField(max_length=14, blank=True, null=True)  
    enti_celu = models.CharField(max_length=15, blank=True, null=True)  
    enti_emai = models.CharField(max_length=100, blank=True, null=True)  
    
    #usuarios do Login de cliente 
    enti_mobi_usua = models.CharField(max_length=100, blank=True, null=True)  
    enti_mobi_senh = models.CharField(max_length=100, blank=True, null=True)
    enti_mobi_prec = models.BooleanField(default=True) # Permissão Preço Usuário 1
    enti_mobi_foto = models.BooleanField(default=True) # Permissão Foto Usuário 1
    
    enti_usua_mobi = models.CharField(max_length=100, blank=True, null=True)
    enti_senh_mobi = models.CharField(max_length=100, blank=True, null=True)
    enti_usua_prec = models.BooleanField(default=True) # Permissão Preço Usuário 2
    enti_usua_foto = models.BooleanField(default=True) # Permissão Foto Usuário 2
    
    enti_vend = models.IntegerField(blank=True, null=True)  
    enti_situ = models.CharField(max_length=100,choices=[('0', 'INATIVO'), ('1', 'ATIVO')], default='1')

    # Campos adicionais para banco/caixa

    enti_banc = models.CharField(max_length=100, blank=True, null=True)
    enti_agen = models.CharField(max_length=100, blank=True, null=True)
    enti_tien = models.CharField(max_length=100, blank=True, null=True, choices=[('B', 'BANCO'), ('C', 'CAIXA'), ('E','Entidade'), ('D','Outros')], default='E')
    enti_diag = models.CharField(max_length=100, blank=True, null=True)
    enti_coco = models.CharField(max_length=100, blank=True, null=True)
    enti_dico = models.CharField(max_length=100, blank=True, null=True)
    
    
    

    objects = SafeMissingColumnsManager()


    def __str__(self):
        return self.enti_nome
    class Meta:
        db_table = 'entidades'
