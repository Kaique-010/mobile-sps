import base64
from io import BytesIO

from django.shortcuts import render
from django.views import View

from core.utils import get_db_from_slug

from .pipeline_entidades import ImportadorEntidadesPipeline
from .preview_pipeline_entidades import PreviewImportadorEntidadesPipeline


class UploadImportadorEntidadesView(View):
    def get(self, request, slug):
        return render(request, "importador_entidades/upload.html")

    def post(self, request, slug):
        file = request.FILES["arquivo"]
        content = file.read()
        request.session["importador_ent_file_b64"] = base64.b64encode(content).decode("ascii")
        request.session["importador_ent_filename"] = file.name

        file_copy = BytesIO(content)
        file_copy.name = file.name
        preview = PreviewImportadorEntidadesPipeline(file_copy).gerar_preview()
        colunas_origem = preview["colunas_origem"]
        preview_rows = [
            [row.get(col, "") for col in colunas_origem]
            for row in preview["preview_linhas"]
        ]

        return render(request, "importador_entidades/preview.html", {
            "slug": slug,
            "pairs": list(zip(preview["colunas_origem"], preview["colunas_mapeadas"])),
            "colunas_origem": colunas_origem,
            "preview_rows": preview_rows,
        })


class ConfirmarImportacaoEntidadesView(View):
    def post(self, request, slug):
        empresa = request.session.get("empresa_id", 1)
        db = get_db_from_slug(slug)

        conteudo_b64 = request.session.get("importador_ent_file_b64")
        filename = request.session.get("importador_ent_filename")
        conteudo = base64.b64decode(conteudo_b64 or "")
        file = BytesIO(conteudo)
        file.name = filename

        pipeline = ImportadorEntidadesPipeline(file, empresa, db)
        resultado = pipeline.processar()

        return render(request, "importador_entidades/resultado.html", {
            "slug": slug,
            "resultado": resultado,
        })
