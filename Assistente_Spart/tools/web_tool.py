import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool


@tool
def procura_web(query: str) -> str:
    """
    Procura a internet usando a api de DuckDuckGo para responder à pergunta do usuário.
    útil para buscas inteligentes e atualizadas sobre assuntos gerais 
    """
    url = f"https://duckduckgo.com/html/?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        return f"Erro ao fazer a requisição: {response.status_code}"
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("div", class_="result")
    if not results:
        return "Nenhum resultado encontrado."
    return results[0].text.strip()

