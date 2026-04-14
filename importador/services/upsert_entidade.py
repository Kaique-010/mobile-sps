from Entidades.models import Entidades


class UpsertEntidade:
    def __init__(self, row, empresa, db):
        self.row = row
        self.empresa = int(empresa)
        self.db = db

    def _proximo_codigo(self):
        ultimo = Entidades.objects.using(self.db).filter(enti_empr=self.empresa).order_by("-enti_clie").first()
        return (int(ultimo.enti_clie) + 1) if ultimo else 1

    def _find_existente(self):
        codigo = self.row.get("enti_clie")
        if str(codigo or "").isdigit():
            entidade = Entidades.objects.using(self.db).filter(enti_empr=self.empresa, enti_clie=int(codigo)).first()
            if entidade:
                return entidade

        cnpj = self.row.get("enti_cnpj")
        if cnpj:
            entidade = Entidades.objects.using(self.db).filter(enti_empr=self.empresa, enti_cnpj=cnpj).first()
            if entidade:
                return entidade

        cpf = self.row.get("enti_cpf")
        if cpf:
            entidade = Entidades.objects.using(self.db).filter(enti_empr=self.empresa, enti_cpf=cpf).first()
            if entidade:
                return entidade

        nome = (self.row.get("enti_nome") or "").strip()
        if nome:
            return Entidades.objects.using(self.db).filter(enti_empr=self.empresa, enti_nome__iexact=nome).first()

        return None

    def executar(self):
        existente = self._find_existente()

        dados = {
            "enti_empr": self.empresa,
            "enti_nome": self.row.get("enti_nome"),
            "enti_tipo_enti": self.row.get("enti_tipo_enti", "CL"),
            "enti_fant": self.row.get("enti_fant"),
            "enti_cpf": self.row.get("enti_cpf"),
            "enti_cnpj": self.row.get("enti_cnpj"),
            "enti_insc_esta": self.row.get("enti_insc_esta"),
            "enti_cep": self.row.get("enti_cep"),
            "enti_ende": self.row.get("enti_ende"),
            "enti_nume": self.row.get("enti_nume"),
            "enti_cida": self.row.get("enti_cida"),
            "enti_esta": self.row.get("enti_esta"),
            "enti_pais": self.row.get("enti_pais", "1058"),
            "enti_codi_pais": self.row.get("enti_codi_pais", "1058"),
            "enti_codi_cida": self.row.get("enti_codi_cida", "0000000"),
            "enti_bair": self.row.get("enti_bair"),
            "enti_comp": self.row.get("enti_comp"),
            "enti_fone": self.row.get("enti_fone"),
            "enti_celu": self.row.get("enti_celu"),
            "enti_emai": self.row.get("enti_emai"),
            "enti_situ": self.row.get("enti_situ", "1"),
        }

        if existente:
            for k, v in dados.items():
                setattr(existente, k, v)
            existente.save(using=self.db)
            return existente, False

        codigo = self.row.get("enti_clie")
        if not str(codigo or "").isdigit():
            codigo = self._proximo_codigo()

        while Entidades.objects.using(self.db).filter(enti_empr=self.empresa, enti_clie=int(codigo)).exists():
            codigo = int(codigo) + 1

        novo = Entidades.objects.using(self.db).create(enti_clie=int(codigo), **dados)
        return novo, True
