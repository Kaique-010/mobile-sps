from django.contrib import admin
from django.db import IntegrityError, connections

from centraldeajuda.models import CentralDeAjuda
from core.utils import get_db_from_slug
from Licencas.models import Usuarios


def _central_db_alias():
    return get_db_from_slug("savexml1") or "save1"


def _fix_pk_sequence(db_alias: str):
    conn = connections[db_alias]
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", ["central_centraldeajuda", "id"])
        row = cursor.fetchone()
        seq_name = row[0] if row else None
        if not seq_name:
            return
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM central_centraldeajuda")
        max_id = int(cursor.fetchone()[0] or 0)
        cursor.execute("SELECT setval(%s, %s, true)", [seq_name, max_id])


@admin.register(CentralDeAjuda)
class CentralDeAjudaAdmin(admin.ModelAdmin):
    list_display = ("id", "cent_empr", "cent_modu", "cent_titu", "cent_data_cria")
    search_fields = ("cent_titu", "cent_cont")
    list_filter = ("cent_modu", "cent_empr")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.using(_central_db_alias())

    def save_model(self, request, obj, form, change):
        db_alias = _central_db_alias()
        try:
            obj.save(using=db_alias)
        except IntegrityError:
            _fix_pk_sequence(db_alias)
            obj.save(using=db_alias)

    def delete_model(self, request, obj):
        obj.delete(using=_central_db_alias())

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "cent_usua_crio":
            kwargs["queryset"] = Usuarios.objects.using(_central_db_alias()).all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
