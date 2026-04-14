import re


ALIAS_ENTIDADES = {
    "codigo": "enti_clie",
    "cod": "enti_clie",
    "id": "enti_clie",
    "id entidade": "enti_clie",
    "entidade": "enti_nome",
    "nome": "enti_nome",
    "razao social": "enti_nome",
    "razao": "enti_nome",
    "nome fantasia": "enti_fant",
    "fantasia": "enti_fant",
    "tipo": "enti_tipo_enti",
    "tipo entidade": "enti_tipo_enti",
    "cpf": "enti_cpf",
    "cnpj": "enti_cnpj",
    "inscricao estadual": "enti_insc_esta",
    "ie": "enti_insc_esta",
    "cep": "enti_cep",
    "endereco": "enti_ende",
    "logradouro": "enti_ende",
    "numero": "enti_nume",
    "cidade": "enti_cida",
    "estado": "enti_esta",
    "uf": "enti_esta",
    "bairro": "enti_bair",
    "complemento": "enti_comp",
    "telefone": "enti_fone",
    "fone": "enti_fone",
    "celular": "enti_celu",
    "email": "enti_emai",
    "e-mail": "enti_emai",
    "situacao": "enti_situ",
    "sit": "enti_situ",
}


class MapeamentoCamposEntidades:
    def __init__(self, df):
        self.df = df

    def normalizar(self, col):
        import unicodedata

        x = str(col).strip().lower()
        x = unicodedata.normalize("NFKD", x)
        x = "".join(c for c in x if not unicodedata.combining(c))
        x = re.sub(r"[^a-z0-9 ]", "", x)
        return x

    def mapear(self):
        novas = []
        contagem = {}
        for col in self.df.columns:
            nome = ALIAS_ENTIDADES.get(self.normalizar(col), self.normalizar(col))
            contagem[nome] = contagem.get(nome, 0) + 1
            if contagem[nome] > 1:
                nome = f"{nome}__{contagem[nome]}"
            novas.append(nome)
        self.df.columns = novas
        return self.df
