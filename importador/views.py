# importador_produtos/views.py

from django.shortcuts import render
from django.views import View
from .preview_pipeline import PreviewImportadorPipeline
from .pipeline import ImportadorProdutosPipeline
import base64
from io import BytesIO
from core.utils import get_licenca_db_config


class UploadImportadorView(View):
    def get(self, request, slug):
        return render(request, "importador/upload.html")

    def post(self, request, slug):
        file = request.FILES["arquivo"]
        content = file.read()
        request.session["importador_file_b64"] = base64.b64encode(content).decode("ascii")
        request.session["importador_filename"] = file.name

        file_copy = BytesIO(content)
        file_copy.name = file.name
        preview = PreviewImportadorPipeline(file_copy).gerar_preview()
        colunas_origem = preview["colunas_origem"]
        colunas_mapeadas = preview["colunas_mapeadas"]
        preview_linhas = preview["preview_linhas"]
        pairs = list(zip(colunas_origem, colunas_mapeadas))
        preview_cells = [
            [row.get(col, "") for col in colunas_origem]
            for row in preview_linhas
        ]
        nome_idx = None
        for i, m in enumerate(colunas_mapeadas):
            if m == "prod_nome":
                nome_idx = i
                break
        dup_raw_values = set()
        dup_count = 0
        if nome_idx is not None:
            import unicodedata, re
            def norm(v):
                s = str(v or "").strip().lower()
                s = unicodedata.normalize('NFKD', s)
                s = ''.join(c for c in s if not unicodedata.combining(c))
                s = re.sub(r"\s+", " ", s)
                return s
            seen = {}
            for r in preview_cells:
                v = r[nome_idx]
                k = norm(v)
                if not k:
                    continue
                if k in seen:
                    dup_raw_values.add(v)
                    dup_raw_values.add(seen[k])
                    dup_count += 1
                else:
                    seen[k] = v
        preview_rows = [{"cells": r, "name": (r[nome_idx] if nome_idx is not None else "")} for r in preview_cells]

        return render(request, "importador/preview.html", {
            "slug": slug,
            "pairs": pairs,
            "colunas_origem": colunas_origem,
            "preview_rows": preview_rows,
            "dup_count": dup_count,
            "dup_values": list(dup_raw_values),
        })


class ConfirmarImportacaoView(View):
    def post(self, request, slug):
        empresa = request.session.get("empresa_id", 1)
        filial = request.session.get("filial_id", 1)
        db = get_licenca_db_config(request)

        # Recuperar arquivo da sessão
        conteudo_b64 = request.session.get("importador_file_b64")
        filename = request.session.get("importador_filename")
        conteudo = base64.b64decode(conteudo_b64 or "")
        file = BytesIO(conteudo)
        file.name = filename

        pipeline = ImportadorProdutosPipeline(file, empresa, filial, db)
        resultado = pipeline.processar()

        return render(request, "importador/resultado.html", {
            "slug": slug,
            "resultado": resultado
        })
