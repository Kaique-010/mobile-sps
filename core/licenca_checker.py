from pathlib import Path
import sqlite3
from decouple import config

BASE_DIR = Path(__file__).resolve().parent

def get_db_name_by_docu(docu: str) -> str | None:
    db_path = BASE_DIR / 'db.sqlite3'
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lice_nome, lice_bloq FROM licencas WHERE lice_docu = ?", (docu,))
        result = cursor.fetchone()
    
    if result:
        lice_nome, bloq = result
        if bloq:
            raise PermissionError("Licença bloqueada.")
        return lice_nome
    return None
