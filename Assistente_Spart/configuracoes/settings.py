import os 
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configurações do aplicativo"""
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    # Adicione outras configurações conforme necessário

settings = Settings()
