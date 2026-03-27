from lxml import etree
from datetime import datetime

from Entidades.models import Entidades
from transportes.models import Veiculos, Mdfeantt, MdfeDocumento

MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"

class MDFeBuilder:

    def __init__(self, mdfe, filial):
        self.mdfe = mdfe
        self.filial = filial
        self.chave = None

    def build(self):
        root = etree.Element("MDFe", nsmap={None: MDFE_NS})

        inf = etree.SubElement(root, "infMDFe")
        inf.set("versao", "3.00")

        chave = self._gerar_chave()
        self.chave = chave
        inf.set("Id", f"MDFe{chave}")

        self._build_ide(inf)
        self._build_emit(inf)
        self._build_modal(inf)
        self._build_doc(inf)

        return etree.tostring(root, encoding="unicode")

    def _build_ide(self, parent):
        ide = etree.SubElement(parent, "ide")

        cuf = self._cuf()
        tp_amb = self._tp_amb()
        tp_emit = (str(self.mdfe.mdf_tipo_emit).strip() if self.mdfe.mdf_tipo_emit is not None else "1") or "1"
        serie = int(self.mdfe.mdf_seri or 1)
        numero = int(self.mdfe.mdf_nume or 0)
        c_mdf = self._cmdf()
        dv = self._dv_da_chave()

        etree.SubElement(ide, "cUF").text = cuf
        etree.SubElement(ide, "tpAmb").text = tp_amb
        etree.SubElement(ide, "tpEmit").text = tp_emit
        etree.SubElement(ide, "mod").text = "58"
        etree.SubElement(ide, "serie").text = f"{serie}"
        etree.SubElement(ide, "nMDF").text = f"{numero}"
        etree.SubElement(ide, "cMDF").text = c_mdf
        etree.SubElement(ide, "cDV").text = dv
        etree.SubElement(ide, "modal").text = "1"
        etree.SubElement(ide, "dhEmi").text = self._dh_emi()
        etree.SubElement(ide, "tpEmis").text = "1"
        etree.SubElement(ide, "procEmi").text = "0"
        etree.SubElement(ide, "verProc").text = "1.0"

        etree.SubElement(ide, "UFIni").text = (self.mdfe.mdf_esta_orig or self.filial.empr_esta or "").strip()
        etree.SubElement(ide, "UFFim").text = (self.mdfe.mdf_esta_dest or "").strip()

        if self.mdfe.mdf_cida_carr and self.mdfe.mdf_nome_carr:
            inf_mun = etree.SubElement(ide, "infMunCarrega")
            etree.SubElement(inf_mun, "cMunCarrega").text = str(self.mdfe.mdf_cida_carr).strip()
            etree.SubElement(inf_mun, "xMunCarrega").text = (self.mdfe.mdf_nome_carr or "").strip()

    def _build_emit(self, parent):
        emit = etree.SubElement(parent, "emit")

        cnpj = getattr(self.filial, "empr_docu", None) or ""
        ie = getattr(self.filial, "empr_insc_esta", None) or ""
        xnome = getattr(self.filial, "empr_nome", None) or ""

        etree.SubElement(emit, "CNPJ").text = str(cnpj).strip()
        etree.SubElement(emit, "IE").text = str(ie).strip()
        etree.SubElement(emit, "xNome").text = str(xnome).strip()

        ender = etree.SubElement(emit, "enderEmit")
        etree.SubElement(ender, "xLgr").text = (self.filial.empr_ende or "").strip()
        etree.SubElement(ender, "nro").text = (self.filial.empr_nume or "").strip() or "S/N"
        etree.SubElement(ender, "xBairro").text = (self.filial.empr_bair or "").strip()
        etree.SubElement(ender, "cMun").text = (self.filial.empr_codi_cida or "").strip()
        etree.SubElement(ender, "xMun").text = (self.filial.empr_cida or "").strip()
        etree.SubElement(ender, "CEP").text = (self.filial.empr_cep or "").strip()
        etree.SubElement(ender, "UF").text = (self.filial.empr_esta or "").strip()
        if self.filial.empr_fone:
            etree.SubElement(ender, "fone").text = str(self.filial.empr_fone).strip()

    def _build_modal(self, parent):
        infModal = etree.SubElement(parent, "infModal")
        infModal.set("versaoModal", "3.00")

        rodo = etree.SubElement(infModal, "rodo")
        rntrc = self._rntrc()
        if rntrc:
            etree.SubElement(rodo, "RNTRC").text = rntrc

        veic_tracao = self._build_veic_tracao(rodo)
        if veic_tracao is not None:
            self._build_condutor(veic_tracao)

    def _build_doc(self, parent):
        infDoc = etree.SubElement(parent, "infDoc")

        db_alias = self.mdfe._state.db or "default"
        try:
            docs = list(MdfeDocumento.objects.using(db_alias).filter(mdfe_id=self.mdfe.mdf_id).all())
        except Exception:
            docs = []

        def limpar_numero(valor):
            raw = str(valor or "").strip()
            return "".join(ch for ch in raw if ch.isdigit())

        grupos = {}
        for doc in docs:
            cmun = (doc.cmun_descarga or self.mdfe.mdf_cida_carr or "").strip()
            xmun = (doc.xmun_descarga or "").strip()
            if not cmun or not xmun:
                continue
            grupos.setdefault((cmun, xmun), []).append(doc)

        if not grupos:
            cmun = (self.mdfe.mdf_cida_carr or "").strip()
            xmun = (self.mdfe.mdf_nome_carr or "").strip()
            if cmun and xmun:
                grupos[(cmun, xmun)] = []

        for (cmun, xmun), itens in grupos.items():
            inf_mun_desc = etree.SubElement(infDoc, "infMunDescarga")
            etree.SubElement(inf_mun_desc, "cMunDescarga").text = str(cmun).strip()
            etree.SubElement(inf_mun_desc, "xMunDescarga").text = str(xmun).strip()

            chaves_usadas = set()
            for item in itens:
                chave = limpar_numero(getattr(item, "chave", None))
                if len(chave) != 44 or not chave.isdigit():
                    continue
                if chave in chaves_usadas:
                    continue
                chaves_usadas.add(chave)

                if getattr(item, "tipo_doc", "00") == "01":
                    inf_cte = etree.SubElement(inf_mun_desc, "infCTe")
                    etree.SubElement(inf_cte, "chCTe").text = chave
                else:
                    inf_nfe = etree.SubElement(inf_mun_desc, "infNFe")
                    etree.SubElement(inf_nfe, "chNFe").text = chave

    def _cuf(self):
        uf = (self.mdfe.mdf_esta_orig or self.filial.empr_esta or "").strip().upper()
        return self._UF_PARA_CUF.get(uf, "35")

    def _gerar_chave(self):
        cuf = self._cuf()
        dt = self.mdfe.mdf_emis or datetime.now().date()
        aamm = dt.strftime("%y%m")

        cnpj = str(getattr(self.filial, "empr_docu", "") or "").strip()
        cnpj = "".join(ch for ch in cnpj if ch.isdigit()).zfill(14)[:14]

        mod = "58"
        serie = str(int(self.mdfe.mdf_seri or 1)).zfill(3)
        nmdf = str(int(self.mdfe.mdf_nume or 0)).zfill(9)
        tp_emis = "1"
        c_mdf = self._cmdf()

        base = f"{cuf}{aamm}{cnpj}{mod}{serie}{nmdf}{tp_emis}{c_mdf}"
        dv = self._calcular_dv(base)
        return f"{base}{dv}"

    def _dv_da_chave(self):
        if self.chave:
            return self.chave[-1:]
        return self._gerar_chave()[-1:]

    def _cmdf(self):
        base = str(int(self.mdfe.mdf_nume or 0)).zfill(9)
        return base[-8:]

    def _dh_emi(self):
        dt = self.mdfe.mdf_emis or datetime.now().date()
        return datetime(dt.year, dt.month, dt.day, datetime.now().hour, datetime.now().minute, datetime.now().second).isoformat()

    def _tp_amb(self):
        val = getattr(self.filial, "empr_ambi_nfe", None)
        if val in ("1", "2"):
            return str(val)
        val_cte = getattr(self.filial, "empr_ambi_cte", None)
        if val_cte in (1, 2, "1", "2"):
            return str(val_cte)
        return "2"

    def _rntrc(self):
        db_alias = self.mdfe._state.db or "default"

        antt = (
            Mdfeantt.objects.using(db_alias)
            .filter(mdfe_antt_mdfe_id=self.mdfe.mdf_id)
            .values_list("mdfe_antt_rntrc", flat=True)
            .first()
        )
        if antt:
            return str(antt).strip()

        if getattr(self.mdfe, "mdf_veic", None) and getattr(self.mdfe, "mdf_tran", None):
            veic = (
                Veiculos.objects.using(db_alias)
                .filter(
                    veic_empr=self.mdfe.mdf_empr,
                    veic_tran=self.mdfe.mdf_tran,
                    veic_sequ=self.mdfe.mdf_veic,
                )
                .values_list("veic_rntr", flat=True)
                .first()
            )
            if veic:
                return str(veic).strip()

        return None

    def _build_veic_tracao(self, rodo_el):
        db_alias = self.mdfe._state.db or "default"

        placa = None
        renavam = None
        uf_veic = None

        if getattr(self.mdfe, "mdf_veic", None) and getattr(self.mdfe, "mdf_tran", None):
            veic = (
                Veiculos.objects.using(db_alias)
                .filter(
                    veic_empr=self.mdfe.mdf_empr,
                    veic_tran=self.mdfe.mdf_tran,
                    veic_sequ=self.mdfe.mdf_veic,
                )
                .first()
            )
            if veic:
                placa = veic.veic_plac
                renavam = veic.veic_rena
                uf_veic = veic.veic_esta

        if not placa:
            placa = getattr(self.mdfe, "mdf_veic_placa", None)
        if not renavam:
            renavam = getattr(self.mdfe, "mdf_veic_renavam", None)

        if not placa:
            return None

        veic = etree.SubElement(rodo_el, "veicTracao")
        if placa:
            etree.SubElement(veic, "placa").text = str(placa).strip().upper()
        if renavam:
            etree.SubElement(veic, "RENAVAM").text = str(renavam).strip()
        uf = (uf_veic or self.mdfe.mdf_esta_orig or self.filial.empr_esta or "").strip().upper()
        if uf:
            etree.SubElement(veic, "UF").text = uf
        return veic

    def _build_condutor(self, veic_tracao_el):
        db_alias = self.mdfe._state.db or "default"

        cpf = None
        nome = None

        if getattr(self.mdfe, "mdf_moto", None):
            motorista = (
                Entidades.objects.using(db_alias)
                .filter(enti_clie=self.mdfe.mdf_moto)
                .values_list("enti_cpf", "enti_nome")
                .first()
            )
            if motorista:
                cpf, nome = motorista

        if not cpf:
            cpf = getattr(self.mdfe, "mdf_moto_cpf", None)
        if not nome:
            nome = getattr(self.mdfe, "mdf_moto_nome", None)

        if not cpf and not nome:
            return

        condutor = etree.SubElement(veic_tracao_el, "condutor")
        if cpf:
            etree.SubElement(condutor, "CPF").text = str(cpf).strip()
        if nome:
            etree.SubElement(condutor, "xNome").text = str(nome).strip()

    def _calcular_dv(self, chave_sem_dv: str) -> str:
        pesos = [2, 3, 4, 5, 6, 7, 8, 9]
        soma = 0
        rev = list(reversed(chave_sem_dv))
        for i, ch in enumerate(rev):
            soma += int(ch) * pesos[i % len(pesos)]
        mod = soma % 11
        dv = 11 - mod
        if dv in (10, 11):
            dv = 0
        return str(dv)

    _UF_PARA_CUF = {
        "RO": "11",
        "AC": "12",
        "AM": "13",
        "RR": "14",
        "PA": "15",
        "AP": "16",
        "TO": "17",
        "MA": "21",
        "PI": "22",
        "CE": "23",
        "RN": "24",
        "PB": "25",
        "PE": "26",
        "AL": "27",
        "SE": "28",
        "BA": "29",
        "MG": "31",
        "ES": "32",
        "RJ": "33",
        "SP": "35",
        "PR": "41",
        "SC": "42",
        "RS": "43",
        "MS": "50",
        "MT": "51",
        "GO": "52",
        "DF": "53",
    }
