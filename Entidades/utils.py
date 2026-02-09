import requests
from Entidades.models import Entidades

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
                "codi_cidade": data.get("ibge") or '000000',

            }
   

    return None

def proxima_entidade(empresa_id, filial_id, banco):
    try:
        ultima_entidade = Entidades.objects.using(banco).filter(
            enti_empr=empresa_id,
        ).order_by('-enti_clie').first()
        
        if ultima_entidade:
            return int(ultima_entidade.enti_clie) + 1
        else:
            return 1
    except Entidades.DoesNotExist:
        return 1

def gerar_cpf_fake():
    import random
    cpf = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
        cpf.append(11 - val if val > 1 else 0)
    return ''.join(map(str, cpf))