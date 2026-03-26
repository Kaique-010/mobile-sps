import logging
from datetime import datetime
import base64
import hashlib
import re
import random
import xml.etree.ElementTree as ET

from transportes.models import Cte, CteDocumento
from Entidades.models import Entidades
from Licencas.models import Filiais

logger = logging.getLogger(__name__)

CTE_NS = "http://www.portalfiscal.inf.br/cte"
ET.register_namespace("", CTE_NS)
HOMOLOG_XNOME = "CTE EMITIDO EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"


class CteXmlBuilder:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self.remetente = None
        self.destinatario = None
        self.expedidor = None
        self.recebedor = None
        self.tomador = None

        # Campos derivados — preenchidos após carregar entidades
        self.cidade_ini_nome = ""
        self.cidade_ini_uf = ""
        self.cidade_fim_nome = ""
        self.cidade_fim_uf = ""

        self._carregar_dados()

    # ------------------------------------------------------------------
    # HELPERS de XML
    # ------------------------------------------------------------------

    def _tag(self, local_name: str) -> str:
        return f"{{{CTE_NS}}}{local_name}"

    def _add(self, parent, tag: str, text=None, attrib=None):
        el = ET.SubElement(parent, self._tag(tag), attrib or {})
        if text is not None and text != "":
            el.text = str(text)
        return el

    def _to_xml(self, root: ET.Element) -> str:
        """
        Gera XML compacto sem indentação, sem quebras de linha e SEM declaração <?xml?>.
        A SEFAZ falha na descompactação se houver whitespace ou pretty-print.
        """
        return ET.tostring(root, encoding="unicode", xml_declaration=False)

    def _fmt(self, v, decimals: int = 2) -> str:
        try:
            n = float(v or 0)
        except Exception:
            n = 0.0
        return f"{n:.{decimals}f}"

    def _mun_ibge7(self, valor, *, fallback: str = "0000000") -> str:
        v = "" if valor is None else str(valor).strip()
        v = self._limpar_numero(v)
        if v.isdigit() and len(v) < 7:
            v = v.zfill(7)
        if v.isdigit() and len(v) == 7:
            return v
        return fallback

    def _limpar_numero(self, valor):
        if not valor:
            return ""
        return re.sub(r'\D', '', str(valor))

    def _calcular_dv_44(self, corpo_43: str) -> str:
        soma = 0
        peso = 2
        for digito in reversed(corpo_43):
            soma += int(digito) * peso
            peso += 1
            if peso > 9:
                peso = 2
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        return str(dv)

    def _chave_valida(self, chave_44: str) -> bool:
        s = self._limpar_numero(chave_44 or "")
        if not s.isdigit() or len(s) != 44:
            return False
        dv_calc = self._calcular_dv_44(s[:43])
        return s[-1] == dv_calc

    def _ajustar_xnome_homologacao(self, xnome: str) -> str:
        tp_amb = str(getattr(self.filial, "empr_ambi_cte", "") or "").strip()
        if tp_amb == "2":
            return HOMOLOG_XNOME
        return xnome
    
    
    def _resolve_cuf(self) -> str:
        cuf = str(getattr(self.filial, "empr_codi_uf", "") or "").strip()
        if cuf.isdigit() and len(cuf) == 2:
            return cuf
        uf_to_cuf = {
            "RO": "11","AC": "12","AM": "13","RR": "14","PA": "15","AP": "16","TO": "17",
            "MA": "21","PI": "22","CE": "23","RN": "24","PB": "25","PE": "26","AL": "27","SE": "28","BA": "29",
            "MG": "31","ES": "32","RJ": "33","SP": "35","PR": "41","SC": "42","RS": "43",
            "MS": "50","MT": "51","GO": "52","DF": "53",
        }
        uf = str(getattr(self.filial, "empr_esta", "") or "").strip().upper()
        return uf_to_cuf.get(uf, "35")

    # ------------------------------------------------------------------
    # CARREGAMENTO DE DADOS
    # ------------------------------------------------------------------

    def _carregar_dados(self):
        """Carrega os dados relacionados necessários para o XML"""
        db_alias = self.cte._state.db or 'default'

        # 1. Filial emitente
        try:
            self.filial = Filiais.objects.using(db_alias).defer('empr_cert_digi').filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).first()
            if not self.filial:
                raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial: {e}")
            raise Exception("Dados da filial emitente não encontrados.")

        # 2. Carregar entidades PRIMEIRO
        if self.cte.remetente:
            self.remetente = Entidades.objects.using(db_alias).filter(
                enti_clie=self.cte.remetente
            ).first()

        if self.cte.destinatario:
            self.destinatario = Entidades.objects.using(db_alias).filter(
                enti_clie=self.cte.destinatario
            ).first()

        if self.cte.tomador_servico == 4 and self.cte.outro_tomador:
            self.tomador = Entidades.objects.using(db_alias).filter(
                enti_clie=self.cte.outro_tomador
            ).first()

        # 3. Derivar nome/UF das cidades DEPOIS de carregar as entidades
        self.cidade_ini_nome = self.remetente.enti_cida if self.remetente else ""
        self.cidade_ini_uf   = self.remetente.enti_esta if self.remetente else ""
        self.cidade_fim_nome = self.destinatario.enti_cida if self.destinatario else ""
        self.cidade_fim_uf   = self.destinatario.enti_esta if self.destinatario else ""

    # ------------------------------------------------------------------
    # BUILD PRINCIPAL
    # ------------------------------------------------------------------

    def build(self) -> str:
        chave, cct, dv = self._gerar_chave_acesso()
        self.cte.chave_de_acesso = chave

        root = ET.Element(self._tag("CTe"))
        inf_cte = self._add(root, "infCte", attrib={"versao": "4.00", "Id": f"CTe{chave}"})

        self._build_ide(inf_cte, cct=cct, dv=dv)
        self._build_emit(inf_cte)
        self._build_rem(inf_cte)
        try:
            toma_val = int(self.cte.tomador_servico or 0)
        except Exception:
            toma_val = 0
        if toma_val == 1:
            self._build_exped(inf_cte)
        self._build_dest(inf_cte)
        if toma_val == 3:
            self._build_receb(inf_cte)
        self._build_vprest(inf_cte)
        self._build_imp(inf_cte)
        self._build_inf_cte_norm(inf_cte)
        self._build_resp_tecnico(inf_cte, chave=chave)

        return self._to_xml(root)

    # ------------------------------------------------------------------
    # CHAVE DE ACESSO
    # ------------------------------------------------------------------

    def _gerar_chave_acesso(self):
        uf = self._resolve_cuf()
        if self.cte.chave_de_acesso and len(self.cte.chave_de_acesso) == 44:
            existente = self.cte.chave_de_acesso
            if existente[:2] == uf:
                return existente, existente[-9:-1], existente[-1]
        agora = datetime.now()
        am = f"{agora.year % 100:02d}{agora.month:02d}"
        cnpj = self._limpar_numero(self.filial.empr_docu).zfill(14)
        mod = (self.cte.modelo or "57").zfill(2)
        serie = str(self.cte.serie or "1").zfill(3)
        nct = str(self.cte.numero).zfill(9)
        tp_emis = str(self.cte.forma_emissao or "1")

        cct = f"{random.randint(0, 99999999):08d}"

        chave_sem_dv = f"{uf}{am}{cnpj}{mod}{serie}{nct}{tp_emis}{cct}"

        soma = 0
        peso = 2
        for digito in reversed(chave_sem_dv):
            soma += int(digito) * peso
            peso += 1
            if peso > 9:
                peso = 2

        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto

        chave = f"{chave_sem_dv}{dv}"
        return chave, cct, str(dv)

    # ------------------------------------------------------------------
    # IDE
    # ------------------------------------------------------------------

    def _build_ide(self, parent, cct: str, dv: str):
        ide = self._add(parent, "ide")
        cuf = self._resolve_cuf()
        self._add(ide, "cUF", cuf)
        self._add(ide, "cCT", str(cct).zfill(8))
        self._add(ide, "CFOP", str(self.cte.cfop or "5353"))
        self._add(ide, "natOp", "PRESTACAO DE SERVICO")
        self._add(ide, "mod", self.cte.modelo or "57")
        self._add(ide, "serie", str(self.cte.serie or "1"))
        self._add(ide, "nCT", str(self.cte.numero))
        self._add(ide, "dhEmi", datetime.now().astimezone().isoformat(timespec="seconds"))
        self._add(ide, "tpImp", "1")
        self._add(ide, "tpEmis", self.cte.forma_emissao or "1")
        self._add(ide, "cDV", dv)
        self._add(ide, "tpAmb", self.filial.empr_ambi_cte or "2")
        def _mapear_tpcte(val):
            try:
                v = int(val or 0)
            except Exception:
                v = 0
            # Model: 1-Normal, 2-Complemento, 3-Anulação, 4-Substituto
            # MOC:   0-Normal, 1-Complementar, 2-Anulação, 3-Substituição
            mapping = {1: "0", 2: "1", 3: "2", 4: "3"}
            return mapping.get(v, "0")
        self._add(ide, "tpCTe", _mapear_tpcte(self.cte.tipo_cte))
        self._add(ide, "procEmi", "0")
        self._add(ide, "verProc", "1.0")
        cmun_env = str(getattr(self.filial, "empr_codi_cida", "") or "").strip()
        if cmun_env.isdigit() and len(cmun_env) < 7:
            cmun_env = cmun_env.zfill(7)
        self._add(ide, "cMunEnv", cmun_env or "0000000")
        self._add(ide, "xMunEnv", self.filial.empr_cida or "")
        self._add(ide, "UFEnv", self.filial.empr_esta or "")
        self._add(ide, "modal", "01")
        self._add(ide, "tpServ", self.cte.tipo_servico or "0")

        # Cidade/UF de coleta
        c_mun_ini = self._mun_ibge7(
            getattr(self.cte, "cidade_coleta", None),
            fallback=self._mun_ibge7(getattr(self.remetente, "enti_codi_cida", None), fallback=self._mun_ibge7(getattr(self.filial, "empr_codi_cida", None))),
        )
        self._add(ide, "cMunIni", c_mun_ini)
        self._add(ide, "xMunIni", self.cidade_ini_nome)
        self._add(ide, "UFIni", self.cidade_ini_uf)

        # Cidade/UF de entrega
        c_mun_fim = self._mun_ibge7(
            getattr(self.cte, "cidade_entrega", None),
            fallback=self._mun_ibge7(getattr(self.destinatario, "enti_codi_cida", None), fallback=self._mun_ibge7(getattr(self.filial, "empr_codi_cida", None))),
        )
        self._add(ide, "cMunFim", c_mun_fim)
        self._add(ide, "xMunFim", self.cidade_fim_nome)
        self._add(ide, "UFFim", self.cidade_fim_uf)

        # retira — campo pode não existir no model ainda
        retira = str(getattr(self.cte, "retira", None) or "0")
        self._add(ide, "retira", retira)

        # xDetRetira só vai quando retira = 0
        if retira == "0":
            det = str(getattr(self.cte, "det_retira", None) or "").strip()
            if det:
                self._add(ide, "xDetRetira", det)

        self._add(ide, "indIEToma", "1")
        self._build_tomador(ide)

    # ------------------------------------------------------------------
    # EMIT
    # ------------------------------------------------------------------

    def _build_emit(self, parent):
        if not self.filial:
            return None

        cnpj = self._limpar_numero(self.filial.empr_docu)

        emit = self._add(parent, "emit")
        self._add(emit, "CNPJ", cnpj)
        self._add(emit, "IE", self._limpar_numero(self.filial.empr_insc_esta))
        self._add(emit, "xNome", self.filial.empr_nome)
        self._add(emit, "xFant", self.filial.empr_fant or self.filial.empr_nome)
        ender_emit = self._add(emit, "enderEmit")
        self._add(ender_emit, "xLgr", self.filial.empr_ende or "")
        self._add(ender_emit, "nro", self.filial.empr_nume or "S/N")
        x_cpl = str(getattr(self.filial, "empr_comp", "") or "").strip()
        if x_cpl:
            self._add(ender_emit, "xCpl", x_cpl)
        self._add(ender_emit, "xBairro", self.filial.empr_bair or "")
        self._add(ender_emit, "cMun", self._mun_ibge7(getattr(self.filial, "empr_codi_cida", None)))
        self._add(ender_emit, "xMun", self.filial.empr_cida or "")
        self._add(ender_emit, "CEP", self._limpar_numero(self.filial.empr_cep))
        self._add(ender_emit, "UF", self.filial.empr_esta or "")
        fone = self._limpar_numero(getattr(self.filial, "empr_fone", "") or "")
        if fone:
            self._add(ender_emit, "fone", fone)
        crt = str(getattr(self.filial, "empr_regi_trib", "") or "").strip()
        if not crt:
            crt = "3"
        self._add(emit, "CRT", crt)
        return emit

    # ------------------------------------------------------------------
    # RESPONSÁVEL TÉCNICO
    # ------------------------------------------------------------------

    def _build_resp_tecnico(self, parent, *, chave: str):
        try:
            from decouple import config
        except Exception:
            config = None

        def cfg(name: str, default=None):
            if not config:
                return default
            try:
                return config(name, default=default)
            except Exception:
                return default

        default_cnpj = "20702018000142"
        default_contato = "DANIEL DIAS DE ALMEIDA"
        default_email = "spartacus@spartacus.com.br"
        default_fone = self._limpar_numero(getattr(self.filial, "empr_fone", "") or "") or "4232236164"

        cnpj = self._limpar_numero(str(cfg("RESP_TEC_CNPJ", default_cnpj) or default_cnpj).strip()) or default_cnpj
        contato = str(cfg("RESP_TEC_CONTATO", default_contato) or default_contato).strip() or default_contato
        email = str(cfg("RESP_TEC_EMAIL", default_email) or default_email).strip() or default_email
        fone = self._limpar_numero(str(cfg("RESP_TEC_FONE", default_fone) or default_fone).strip()) or default_fone

        id_csrt = str(cfg("CSRT_ID", "") or "").strip() or None
        csrt_key = str(cfg("CSRT_KEY", "") or "").strip() or None

        tp_amb = str(getattr(self.filial, "empr_ambi_cte", "") or "").strip()
        if tp_amb == "1":
            id_csrt = id_csrt or (str(cfg("CSRT_ID_PRODUCAO", "") or "").strip() or None)
            csrt_key = csrt_key or (str(cfg("CSRT_KEY_PRODUCAO", "") or "").strip() or None)
        else:
            id_csrt = id_csrt or (str(cfg("CSRT_ID_HOMOLOGACAO", "") or "").strip() or None)
            csrt_key = csrt_key or (str(cfg("CSRT_KEY_HOMOLOGACAO", "") or "").strip() or None)

        if not id_csrt and hasattr(self.filial, "empr_csrt_id"):
            id_csrt = str(getattr(self.filial, "empr_csrt_id") or "").strip() or None
        if not csrt_key and hasattr(self.filial, "empr_csrt_key"):
            csrt_key = str(getattr(self.filial, "empr_csrt_key") or "").strip() or None

        hash_csrt = None
        if csrt_key and id_csrt:
            data = f"{csrt_key}{chave}"
            hash_bytes = hashlib.sha1(data.encode("utf-8")).digest()
            hash_csrt = base64.b64encode(hash_bytes).decode("utf-8")

        resp = self._add(parent, "infRespTec")
        self._add(resp, "CNPJ", cnpj)
        self._add(resp, "xContato", contato)
        self._add(resp, "email", email)
        self._add(resp, "fone", fone)
        if id_csrt:
            id_txt = str(id_csrt).strip()
            if id_txt.isdigit() and len(id_txt) < 2:
                id_txt = id_txt.zfill(2)
            self._add(resp, "idCSRT", id_txt)
            if hash_csrt:
                self._add(resp, "hashCSRT", hash_csrt)
        return resp

    # ------------------------------------------------------------------
    # REMETENTE
    # ------------------------------------------------------------------

    def _build_rem(self, parent):
        if not self.remetente:
            return None

        cnpj = self._limpar_numero(self.remetente.enti_cnpj)
        cpf = self._limpar_numero(self.remetente.enti_cpf)

        rem = self._add(parent, "rem")
        if cnpj:
            self._add(rem, "CNPJ", cnpj)
        elif cpf:
            self._add(rem, "CPF", cpf)
        ie = self._limpar_numero(getattr(self.remetente, "enti_insc_esta", "") or "")
        if ie:
            self._add(rem, "IE", ie)
        self._add(rem, "xNome", self._ajustar_xnome_homologacao(self.remetente.enti_nome))
        ender = self._add(rem, "enderReme")
        self._add(ender, "xLgr", self.remetente.enti_ende or "")
        self._add(ender, "nro", self.remetente.enti_nume or "S/N")
        x_cpl = str(getattr(self.remetente, "enti_comp", "") or "").strip()
        if x_cpl:
            self._add(ender, "xCpl", x_cpl)
        bairro = str(getattr(self.remetente, "enti_bair", "") or "").strip()
        self._add(ender, "xBairro", bairro or "NAO INFORMADO")
        self._add(ender, "cMun", self._mun_ibge7(getattr(self.remetente, "enti_codi_cida", None)))
        self._add(ender, "xMun", self.remetente.enti_cida or "")
        self._add(ender, "CEP", self._limpar_numero(self.remetente.enti_cep))
        self._add(ender, "UF", self.remetente.enti_esta or "")
        if hasattr(self.remetente, 'enti_fone'):
            fone = self._limpar_numero(getattr(self.remetente, "enti_fone", "") or "")
            if fone:
                self._add(ender, "fone", fone)
        return rem

    def _build_exped(self, parent):
        fonte = self.remetente
        if not fonte:
            return None
        cnpj = self._limpar_numero(getattr(fonte, "enti_cnpj", None))
        cpf = self._limpar_numero(getattr(fonte, "enti_cpf", None))
        exped = self._add(parent, "exped")
        if cnpj:
            self._add(exped, "CNPJ", cnpj)
        elif cpf:
            self._add(exped, "CPF", cpf)
        ie = self._limpar_numero(getattr(fonte, "enti_insc_esta", "") or "")
        if ie:
            self._add(exped, "IE", ie)
        self._add(exped, "xNome", self._ajustar_xnome_homologacao(getattr(fonte, "enti_nome", "")))
        ender = self._add(exped, "enderExped")
        self._add(ender, "xLgr", getattr(fonte, "enti_ende", "") or "")
        self._add(ender, "nro", getattr(fonte, "enti_nume", "") or "S/N")
        x_cpl = str(getattr(fonte, "enti_comp", "") or "").strip()
        if x_cpl:
            self._add(ender, "xCpl", x_cpl)
        bairro = str(getattr(fonte, "enti_bair", "") or "").strip()
        self._add(ender, "xBairro", bairro or "NAO INFORMADO")
        self._add(ender, "cMun", self._mun_ibge7(getattr(fonte, "enti_codi_cida", None)))
        self._add(ender, "xMun", getattr(fonte, "enti_cida", "") or "")
        self._add(ender, "CEP", self._limpar_numero(getattr(fonte, "enti_cep", None)))
        self._add(ender, "UF", getattr(fonte, "enti_esta", "") or "")
        if hasattr(fonte, 'enti_fone'):
            fone = self._limpar_numero(getattr(fonte, "enti_fone", "") or "")
            if fone:
                self._add(ender, "fone", fone)
        return exped

    # ------------------------------------------------------------------
    # DESTINATÁRIO
    # ------------------------------------------------------------------

    def _build_dest(self, parent):
        if not self.destinatario:
            return None

        cnpj = self._limpar_numero(self.destinatario.enti_cnpj)
        cpf = self._limpar_numero(self.destinatario.enti_cpf)

        dest = self._add(parent, "dest")
        if cnpj:
            self._add(dest, "CNPJ", cnpj)
        elif cpf:
            self._add(dest, "CPF", cpf)
        ie = self._limpar_numero(getattr(self.destinatario, "enti_insc_esta", "") or "")
        if ie:
            self._add(dest, "IE", ie)
        self._add(dest, "xNome", self._ajustar_xnome_homologacao(self.destinatario.enti_nome))
        ender = self._add(dest, "enderDest")
        self._add(ender, "xLgr", self.destinatario.enti_ende or "")
        self._add(ender, "nro", self.destinatario.enti_nume or "S/N")
        x_cpl = str(getattr(self.destinatario, "enti_comp", "") or "").strip()
        if x_cpl:
            self._add(ender, "xCpl", x_cpl)
        bairro = str(getattr(self.destinatario, "enti_bair", "") or "").strip()
        self._add(ender, "xBairro", bairro or "NAO INFORMADO")
        self._add(ender, "cMun", self._mun_ibge7(getattr(self.destinatario, "enti_codi_cida", None)))
        self._add(ender, "xMun", self.destinatario.enti_cida or "")
        self._add(ender, "CEP", self._limpar_numero(self.destinatario.enti_cep))
        self._add(ender, "UF", self.destinatario.enti_esta or "")
        if hasattr(self.destinatario, 'enti_fone'):
            fone = self._limpar_numero(getattr(self.destinatario, "enti_fone", "") or "")
            if fone:
                self._add(ender, "fone", fone)
        return dest

    def _build_receb(self, parent):
        fonte = self.destinatario
        if not fonte:
            return None
        cnpj = self._limpar_numero(getattr(fonte, "enti_cnpj", None))
        cpf = self._limpar_numero(getattr(fonte, "enti_cpf", None))
        receb = self._add(parent, "receb")
        if cnpj:
            self._add(receb, "CNPJ", cnpj)
        elif cpf:
            self._add(receb, "CPF", cpf)
        ie = self._limpar_numero(getattr(fonte, "enti_insc_esta", "") or "")
        if ie:
            self._add(receb, "IE", ie)
        self._add(receb, "xNome", self._ajustar_xnome_homologacao(getattr(fonte, "enti_nome", "")))
        ender = self._add(receb, "enderReceb")
        self._add(ender, "xLgr", getattr(fonte, "enti_ende", "") or "")
        self._add(ender, "nro", getattr(fonte, "enti_nume", "") or "S/N")
        x_cpl = str(getattr(fonte, "enti_comp", "") or "").strip()
        if x_cpl:
            self._add(ender, "xCpl", x_cpl)
        bairro = str(getattr(fonte, "enti_bair", "") or "").strip()
        self._add(ender, "xBairro", bairro or "NAO INFORMADO")
        self._add(ender, "cMun", self._mun_ibge7(getattr(fonte, "enti_codi_cida", None)))
        self._add(ender, "xMun", getattr(fonte, "enti_cida", "") or "")
        self._add(ender, "CEP", self._limpar_numero(getattr(fonte, "enti_cep", None)))
        self._add(ender, "UF", getattr(fonte, "enti_esta", "") or "")
        if hasattr(fonte, 'enti_fone'):
            fone = self._limpar_numero(getattr(fonte, "enti_fone", "") or "")
            if fone:
                self._add(ender, "fone", fone)
        return receb

    # ------------------------------------------------------------------
    # VALORES DA PRESTAÇÃO
    # ------------------------------------------------------------------

    def _build_vprest(self, parent):
        comps = []
        if self.cte.frete_valor:
            comps.append(("Frete Valor", self._fmt(self.cte.frete_valor)))
        if self.cte.pedagio:
            comps.append(("Pedagio", self._fmt(self.cte.pedagio)))

        if not comps:
            comps.append(("Frete Peso", self._fmt(self.cte.total_valor)))

        vprest = self._add(parent, "vPrest")
        self._add(vprest, "vTPrest", self._fmt(self.cte.total_valor))
        self._add(vprest, "vRec", self._fmt(self.cte.liquido_a_receber))
        for nome, valor in comps:
            comp_el = self._add(vprest, "Comp")
            self._add(comp_el, "xNome", nome)
            self._add(comp_el, "vComp", valor)
        return vprest

    # ------------------------------------------------------------------
    # IMPOSTOS
    # ------------------------------------------------------------------

    def _build_imp(self, parent):
        cst = str(self.cte.cst_icms or "00").strip() or "00"

        imp = self._add(parent, "imp")
        icms = self._add(imp, "ICMS")

        simples_codes = {"101","102","103","201","202","203","300","400","500","900"}
        if cst in simples_codes:
            icms_group = self._add(icms, "ICMSSN")
            self._add(icms_group, "CST", "90")
            self._add(icms_group, "indSN", "1")
            if self.cte.valor_icms_uf_dest and float(self.cte.valor_icms_uf_dest) > 0:
                icms_uf_dest = self._add(imp, "ICMSUFDest")
                self._add(icms_uf_dest, "vBCUFDest", self._fmt(self.cte.valor_bc_uf_dest))
                self._add(icms_uf_dest, "vBCFCPUFDest", self._fmt(self.cte.valor_bc_uf_dest))
                self._add(icms_uf_dest, "pFCPUFDest", "0.00")
                self._add(icms_uf_dest, "pICMSUFDest", self._fmt(self.cte.aliquota_interna_dest))
                self._add(icms_uf_dest, "pICMSInter", self._fmt(self.cte.aliquota_interestadual))
                self._add(icms_uf_dest, "pICMSInterPart", "100.00")
                self._add(icms_uf_dest, "vFCPUFDest", "0.00")
                self._add(icms_uf_dest, "vICMSUFDest", self._fmt(self.cte.valor_icms_uf_dest))
                self._add(icms_uf_dest, "vICMSUFRemet", "0.00")
            self._build_ibscbs(imp)
            self._build_inf_trib_fed(imp)
            return imp

        if cst == "00":
            icms_group = self._add(icms, "ICMS00")
        elif cst == "20":
            icms_group = self._add(icms, "ICMS20")
        elif cst in {"40", "41", "51"}:
            icms_group = self._add(icms, "ICMS45")
        elif cst == "60":
            icms_group = self._add(icms, "ICMS60")
        else:
            icms_group = self._add(icms, "ICMS90")

        self._add(icms_group, "CST", cst)

        if cst in {"00", "20", "90", "10", "70"}:
            self._add(icms_group, "vBC", self._fmt(self.cte.base_icms))
            self._add(icms_group, "pICMS", self._fmt(self.cte.aliq_icms))
            self._add(icms_group, "vICMS", self._fmt(self.cte.valor_icms))

        if cst == "20":
            self._add(icms_group, "pRedBC", self._fmt(self.cte.reducao_icms))

        if cst in {"10", "70", "90"}:
            if self.cte.base_icms_st and float(self.cte.base_icms_st) > 0:
                self._add(icms_group, "vBCST", self._fmt(self.cte.base_icms_st))
                self._add(icms_group, "pICMSST", self._fmt(self.cte.aliquota_icms_st))
                self._add(icms_group, "vICMSST", self._fmt(self.cte.valor_icms_st))
                self._add(icms_group, "pMVAST", self._fmt(self.cte.margem_valor_adicionado_st))
                self._add(icms_group, "pRedBCST", self._fmt(self.cte.reducao_base_icms_st))
            if self.cte.reducao_icms and float(self.cte.reducao_icms) > 0:
                self._add(icms_group, "pRedBC", self._fmt(self.cte.reducao_icms))

        if self.cte.valor_icms_uf_dest and float(self.cte.valor_icms_uf_dest) > 0:
            icms_uf_dest = self._add(imp, "ICMSUFDest")
            self._add(icms_uf_dest, "vBCUFDest", self._fmt(self.cte.valor_bc_uf_dest))
            self._add(icms_uf_dest, "vBCFCPUFDest", self._fmt(self.cte.valor_bc_uf_dest))
            self._add(icms_uf_dest, "pFCPUFDest", "0.00")
            self._add(icms_uf_dest, "pICMSUFDest", self._fmt(self.cte.aliquota_interna_dest))
            self._add(icms_uf_dest, "pICMSInter", self._fmt(self.cte.aliquota_interestadual))
            self._add(icms_uf_dest, "pICMSInterPart", "100.00")
            self._add(icms_uf_dest, "vFCPUFDest", "0.00")
            self._add(icms_uf_dest, "vICMSUFDest", self._fmt(self.cte.valor_icms_uf_dest))
            self._add(icms_uf_dest, "vICMSUFRemet", "0.00")

        self._build_ibscbs(imp)
        self._build_inf_trib_fed(imp)
        return imp

    def _build_ibscbs(self, parent):
        if (
            not getattr(self.cte, "ibscbs_cst", None)
            and not getattr(self.cte, "ibscbs_cclasstrib", None)
            and not getattr(self.cte, "ibscbs_vbc", None)
        ):
            return None

        ibscbs = self._add(parent, "IBSCBS")
        if getattr(self.cte, "ibscbs_cst", None):
            self._add(ibscbs, "CST", self.cte.ibscbs_cst)
        if getattr(self.cte, "ibscbs_cclasstrib", None):
            self._add(ibscbs, "cClassTrib", self.cte.ibscbs_cclasstrib)

        g_ibscbs = self._add(ibscbs, "gIBSCBS")
        self._add(g_ibscbs, "vBC", self._fmt(getattr(self.cte, "ibscbs_vbc", None)))

        self._build_g_ibs_uf(g_ibscbs)
        self._build_g_ibs_mun(g_ibscbs)
        self._build_g_cbs(g_ibscbs)
        return ibscbs

    def _build_g_ibs_uf(self, parent):
        fields = [
            getattr(self.cte, "ibs_pibsuf", None),
            getattr(self.cte, "ibs_preduf", None),
            getattr(self.cte, "ibs_paliqefetuf", None),
            getattr(self.cte, "ibs_vibsuf", None),
            getattr(self.cte, "ibs_pdifuf", None),
            getattr(self.cte, "ibs_vdifuf", None),
            getattr(self.cte, "ibs_vdevtribuf", None),
        ]
        if not any(v not in (None, "", 0, 0.0) for v in fields):
            return None

        g = self._add(parent, "gIBSUF")
        if getattr(self.cte, "ibs_pibsuf", None) is not None:
            self._add(g, "pIBSUF", self._fmt(self.cte.ibs_pibsuf))
        if getattr(self.cte, "ibs_preduf", None) is not None:
            self._add(g, "pRedUF", self._fmt(self.cte.ibs_preduf))
        if getattr(self.cte, "ibs_paliqefetuf", None) is not None:
            self._add(g, "pAliqEfetUF", self._fmt(self.cte.ibs_paliqefetuf))
        if getattr(self.cte, "ibs_vibsuf", None) is not None:
            self._add(g, "vIBSUF", self._fmt(self.cte.ibs_vibsuf))
        if getattr(self.cte, "ibs_pdifuf", None) is not None:
            self._add(g, "pDifUF", self._fmt(self.cte.ibs_pdifuf))
        if getattr(self.cte, "ibs_vdifuf", None) is not None:
            self._add(g, "vDifUF", self._fmt(self.cte.ibs_vdifuf))
        if getattr(self.cte, "ibs_vdevtribuf", None) is not None:
            self._add(g, "vDevTribUF", self._fmt(self.cte.ibs_vdevtribuf))
        return g

    def _build_g_ibs_mun(self, parent):
        fields = [
            getattr(self.cte, "ibs_pibsmun", None),
            getattr(self.cte, "ibs_predmun", None),
            getattr(self.cte, "ibs_paliqefetmun", None),
            getattr(self.cte, "ibs_vibsmun", None),
            getattr(self.cte, "ibs_pdifmun", None),
            getattr(self.cte, "ibs_vdifmun", None),
            getattr(self.cte, "ibs_vdevtribmun", None),
        ]
        if not any(v not in (None, "", 0, 0.0) for v in fields):
            return None

        g = self._add(parent, "gIBSMun")
        if getattr(self.cte, "ibs_pibsmun", None) is not None:
            self._add(g, "pIBSMun", self._fmt(self.cte.ibs_pibsmun))
        if getattr(self.cte, "ibs_predmun", None) is not None:
            self._add(g, "pRedMun", self._fmt(self.cte.ibs_predmun))
        if getattr(self.cte, "ibs_paliqefetmun", None) is not None:
            self._add(g, "pAliqEfetMun", self._fmt(self.cte.ibs_paliqefetmun))
        if getattr(self.cte, "ibs_vibsmun", None) is not None:
            self._add(g, "vIBSMun", self._fmt(self.cte.ibs_vibsmun))
        if getattr(self.cte, "ibs_pdifmun", None) is not None:
            self._add(g, "pDifMun", self._fmt(self.cte.ibs_pdifmun))
        if getattr(self.cte, "ibs_vdifmun", None) is not None:
            self._add(g, "vDifMun", self._fmt(self.cte.ibs_vdifmun))
        if getattr(self.cte, "ibs_vdevtribmun", None) is not None:
            self._add(g, "vDevTribMun", self._fmt(self.cte.ibs_vdevtribmun))
        return g

    def _build_g_cbs(self, parent):
        fields = [
            getattr(self.cte, "cbs_pcbs", None),
            getattr(self.cte, "cbs_pred", None),
            getattr(self.cte, "cbs_paliqefet", None),
            getattr(self.cte, "cbs_vcbs", None),
            getattr(self.cte, "cbs_pdif", None),
            getattr(self.cte, "cbs_vdif", None),
            getattr(self.cte, "cbs_vdevtrib", None),
        ]
        if not any(v not in (None, "", 0, 0.0) for v in fields):
            return None

        g = self._add(parent, "gCBS")
        if getattr(self.cte, "cbs_pcbs", None) is not None:
            self._add(g, "pCBS", self._fmt(self.cte.cbs_pcbs))
        if getattr(self.cte, "cbs_pred", None) is not None:
            self._add(g, "pRedCBS", self._fmt(self.cte.cbs_pred))
        if getattr(self.cte, "cbs_paliqefet", None) is not None:
            self._add(g, "pAliqEfetCBS", self._fmt(self.cte.cbs_paliqefet))
        if getattr(self.cte, "cbs_vcbs", None) is not None:
            self._add(g, "vCBS", self._fmt(self.cte.cbs_vcbs))
        if getattr(self.cte, "cbs_pdif", None) is not None:
            self._add(g, "pDif", self._fmt(self.cte.cbs_pdif))
        if getattr(self.cte, "cbs_vdif", None) is not None:
            self._add(g, "vDif", self._fmt(self.cte.cbs_vdif))
        if getattr(self.cte, "cbs_vdevtrib", None) is not None:
            self._add(g, "vDevTrib", self._fmt(self.cte.cbs_vdevtrib))
        return g

    def _build_inf_trib_fed(self, parent):
        v_pis = getattr(self.cte, "valor_pis", None)
        v_cofins = getattr(self.cte, "valor_cofins", None)
        if not (v_pis not in (None, "", 0, 0.0) or v_cofins not in (None, "", 0, 0.0)):
            return None

        inf_trib_fed = self._add(parent, "infTribFed")
        if v_pis not in (None, "", 0, 0.0):
            self._add(inf_trib_fed, "vPIS", self._fmt(v_pis))
        if v_cofins not in (None, "", 0, 0.0):
            self._add(inf_trib_fed, "vCOFINS", self._fmt(v_cofins))
        return inf_trib_fed

    # ------------------------------------------------------------------
    # INF CTE NORM
    # ------------------------------------------------------------------

    def _build_inf_cte_norm(self, parent):
        inf_cte_norm = self._add(parent, "infCTeNorm")
        self._build_inf_carga(inf_cte_norm)
        self._build_inf_doc(inf_cte_norm)

        inf_modal = self._add(inf_cte_norm, "infModal", attrib={"versaoModal": "4.00"})
        rodo = self._add(inf_modal, "rodo")
        self._add(rodo, "RNTRC", getattr(self.cte, 'rntrc', None) or '00000000')
        return inf_cte_norm

    def _build_inf_carga(self, parent):
        inf_carga = self._add(parent, "infCarga")
        self._add(inf_carga, "vCarga", self._fmt(self.cte.total_mercadoria))
        self._add(inf_carga, "proPred", self.cte.produto_predominante or "DIVERSOS")

        inf_q = self._add(inf_carga, "infQ")
        self._add(inf_q, "cUnid", "01")
        self._add(inf_q, "tpMed", "PESO BRUTO")
        self._add(inf_q, "qCarga", self._fmt(self.cte.peso_total, decimals=4) if self.cte.peso_total else "0.0000")

        return inf_carga

    def _build_inf_doc(self, parent):
        db_alias = self.cte._state.db or 'default'
        docs = self.cte.documentos.using(db_alias).all()
        chaves = []
        if not docs:
            logger.info("CT-e: nenhum documento NFe vinculado.")
        for doc in docs:
            raw = getattr(doc, "chave_nfe", None)
            if not raw:
                logger.info("CT-e: documento sem chave_nfe. Ignorado.")
                continue
            chave_num = self._limpar_numero(raw)
            if not chave_num.isdigit():
                logger.info(f"CT-e: chave NFe invalida (nao numerica): {raw}. Ignorada.")
                continue
            if len(chave_num) < 44:
                logger.info(f"CT-e: chave NFe com tamanho invalido ({len(chave_num)}): {raw}. Ignorada.")
                continue
            if len(chave_num) > 44:
                logger.info(f"CT-e: chave NFe com tamanho maior que 44 ({len(chave_num)}): {raw}. Sera truncada para 44.")
                chave_num = chave_num[:44]
            if not self._chave_valida(chave_num):
                logger.info(f"CT-e: chave NFe com DV invalido: {raw}. Ignorada.")
                continue
            chaves.append(chave_num)

        if not chaves:
            logger.info("CT-e: nenhuma chave NFe valida encontrada para infDoc.")
            return None

        inf_doc = self._add(parent, "infDoc")
        for chave in chaves:
            inf_nfe = self._add(inf_doc, "infNFe")
            self._add(inf_nfe, "chave", chave)
            logger.info(f"CT-e: chave NFe incluida: {chave}")
        return inf_doc

    # ------------------------------------------------------------------
    # TOMADOR
    # ------------------------------------------------------------------

    def _build_tomador(self, parent):
        toma = self.cte.tomador_servico
        if toma in [0, 1, 2, 3]:
            toma3 = self._add(parent, "toma3")
            self._add(toma3, "toma", str(toma))
            return toma3
        if toma == 4:
            return self._build_toma4(parent)
        return None

    def _build_toma4(self, parent):
        if not self.tomador:
            return None

        cnpj = self._limpar_numero(self.tomador.enti_cnpj)
        cpf = self._limpar_numero(self.tomador.enti_cpf)

        toma4 = self._add(parent, "toma4")
        self._add(toma4, "toma", "4")
        if cnpj:
            self._add(toma4, "CNPJ", cnpj)
        elif cpf:
            self._add(toma4, "CPF", cpf)
        ie = self._limpar_numero(getattr(self.tomador, "enti_insc_esta", "") or "")
        if ie:
            self._add(toma4, "IE", ie)
        self._add(toma4, "xNome", self._ajustar_xnome_homologacao(self.tomador.enti_nome))
        ender = self._add(toma4, "enderToma")
        self._add(ender, "xLgr", self.tomador.enti_ende or "")
        self._add(ender, "nro", self.tomador.enti_nume or "S/N")
        x_cpl = str(getattr(self.tomador, "enti_comp", "") or "").strip()
        if x_cpl:
            self._add(ender, "xCpl", x_cpl)
        bairro = str(getattr(self.tomador, "enti_bair", "") or "").strip()
        self._add(ender, "xBairro", bairro or "NAO INFORMADO")
        self._add(ender, "cMun", self._mun_ibge7(getattr(self.tomador, "enti_codi_cida", None)))
        self._add(ender, "xMun", self.tomador.enti_cida or "")
        self._add(ender, "CEP", self._limpar_numero(self.tomador.enti_cep))
        self._add(ender, "UF", self.tomador.enti_esta or "")
        if hasattr(self.tomador, 'enti_fone'):
            fone = self._limpar_numero(getattr(self.tomador, "enti_fone", "") or "")
            if fone:
                self._add(ender, "fone", fone)
        return toma4
