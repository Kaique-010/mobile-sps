import requests

def buscar_endereco_por_cep(cep):
    cep = ''.join(filter(str.isdigit, cep))  
    url = f"https://viacep.com.br/ws/{cep}/json/"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "erro" not in data:
            return {
                "cep": data.get("cep"),
                "logradouro": data.get("logradouro"),
                "complemento": data.get("complemento"),
                "bairro": data.get("bairro"),
                "cidade": data.get("localidade"),
                "estado": data.get("uf"),
                "pais": data.get("pais") or '1058',
                "codi_pais": data.get("pais") or '1058',

            }
   

    return None
