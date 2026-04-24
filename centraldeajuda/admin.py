from django.contrib import admin
from django.db import IntegrityError, connections
from django.http import HttpResponse
from openpyxl import Workbook

from centraldeajuda.models import CentralDeAjuda
from core.utils import get_db_from_slug
from Licencas.models import Usuarios


def _central_db_alias():
    return get_db_from_slug("savexml1") or "save1"


def _fix_pk_sequence(db_alias: str):
    conn = connections[db_alias]

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_serial_sequence(%s, %s)",
            ["central_centraldeajuda", "id"]
        )
        row = cursor.fetchone()
        seq_name = row[0] if row else None

        if not seq_name:
            return

        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM central_centraldeajuda")
        max_id = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT setval(%s, %s, true)", [seq_name, max_id])


def excel_value(value):
    if value is None:
        return None

    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        return value.replace(tzinfo=None)

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


@admin.register(CentralDeAjuda)
class CentralDeAjudaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cent_empr",
        "cent_modu",
        "cent_titu",
        "cent_data_cria",
        "cent_data_atual",
        "cent_usua_crio",
        "cent_video",
    )

    search_fields = ("cent_titu", "cent_cont")
    list_filter = ("cent_modu", "cent_empr")
    actions = ["exportar_xlsx"]

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

    def exportar_xlsx(self, request, queryset):
        wb = Workbook()
        ws = wb.active
        ws.title = "Central de Ajuda"

        ws.append([
            "id",
            "empresa",
            "módulo",
            "titulo",
            "conteudo",
            "data de criação",
            "data de atualização",
            "usuário criador",
            "video",
        ])

        for obj in queryset:
            ws.append([
                excel_value(obj.id),
                excel_value(obj.cent_empr),
                excel_value(obj.cent_modu),
                excel_value(obj.cent_titu),
                excel_value(obj.cent_cont),
                excel_value(obj.cent_data_cria),
                excel_value(obj.cent_data_atual),
                excel_value(obj.cent_usua_crio),
                excel_value(obj.cent_video),
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="central_de_ajuda.xlsx"'

        wb.save(response)
        return response

    exportar_xlsx.short_description = "Exportar selecionados para Excel (.xlsx)"