from langchain_core.tools import tool

@tool
def ler_documentos(file_path: str) -> str:
    """
    Lê documentos de um diretório específico com base na consulta do usuário.
    útil para recuperar informações de arquivos locais.
    """
    try:
        with open(file_path,"r",encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Documento {file_path} não encontrado."
