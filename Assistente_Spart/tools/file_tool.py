from langchain_core.tools import tool

@tool
def ler_documentos(file_path: str) -> str:
    """
    Lê documentos locais por caminho absoluto/relativo.
    Condições de uso:
    - Use quando o usuário referenciar um arquivo específico ou solicitar leitura local.
    - Não use para dados de negócio em banco; prefira `consulta_inteligente_prime`.
    - Retorna o conteúdo bruto do arquivo como texto.
    """
    try:
        with open(file_path,"r",encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Documento {file_path} não encontrado."
