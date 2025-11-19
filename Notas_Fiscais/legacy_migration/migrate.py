from .reader_legado import NotaLegadoReader
from .transformers import NotaTransformer
from .writer_novo import NotaWriter


def migrar_notas(banco="default", limite=100):

    reader = NotaLegadoReader(banco)
    registros = reader.listar_notas(limite=limite)

    print(f"🔵 Migrando {len(registros)} notas...")

    for raw in registros:
        emitente_data = NotaTransformer.emitente(raw)
        destinatario_data = NotaTransformer.destinatario(raw)
        nota_data = NotaTransformer.nota(raw, emitente_data, destinatario_data)

        emitente = NotaWriter.salvar_emitente(emitente_data)
        destinatario = NotaWriter.salvar_destinatario(destinatario_data)
        nota = NotaWriter.salvar_nota(nota_data, emitente, destinatario)

        print(f"🟢 NF {nota.modelo}/{nota.serie}/{nota.numero} migrada.")

    print("🏁 Migração concluída.")