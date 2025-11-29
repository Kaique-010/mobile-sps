# -*- coding: utf-8 -*-
"""
Webservices NFC-e 4.00 por UF.
Mesma estrutura do urls_sefaz.py, mas própria para NFC-e.
"""

URLS_NFCE = {
    "AC": {
        "autorizacao_producao":    "https://nfce.sefaznet.ac.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://hml.sefaznet.ac.gov.br/nfce/services/NFeAutorizacao4",
    },
    "AL": {
        "autorizacao_producao":    "https://nfce.sefaz.al.gov.br/nfce-services/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfce.sefaz.al.gov.br/nfce-services/services/NFeAutorizacao4",
    },
    "AM": {
        "autorizacao_producao":    "https://nfce.sefaz.am.gov.br/services2/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://hom_nfce.sefaz.am.gov.br/services2/services/NFeAutorizacao4",
    },
    "AP": {
        "autorizacao_producao":    "https://www.sefaz.ap.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://www.sefaz.ap.gov.br/nfce/services/NFeAutorizacao4",
    },
    "BA": {
        "autorizacao_producao":    "https://nfce.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://hnfce.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
    },
    "CE": {
        "autorizacao_producao":    "https://nfce.sefaz.ce.gov.br/nfce4/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfce.sefaz.ce.gov.br/nfce4/services/NFeAutorizacao4",
    },
    "DF": {
        "autorizacao_producao":    "https://www.fazenda.df.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://www.fazenda.df.gov.br/nfce/services/NFeAutorizacao4",
    },
    "ES": {
        "autorizacao_producao":    "https://nfce.sefaz.es.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://homologacao.sefaz.es.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
    },
    "GO": {
        "autorizacao_producao":    "https://nfe.sefaz.go.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://homolog.sefaz.go.gov.br/nfce/services/NFeAutorizacao4",
    },
    "MA": {
        "autorizacao_producao":    "https://www.sefaz.ma.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://www.sefaz.ma.gov.br/nfce/services/NFeAutorizacao4",
    },
    "MG": {
        # ⚠️ Minas NÃO usa NFC-e (usa SAT Fiscal próprio)
        "autorizacao_producao":    None,
        "autorizacao_homologacao": None,
    },
    "MS": {
        "autorizacao_producao":    "https://nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
        "autorizacao_homologacao": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
    },
    "MT": {
        "autorizacao_producao":    "https://nfce.sefaz.mt.gov.br/nfcews/v2/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://homologacao.sefaz.mt.gov.br/nfcews/v2/services/NFeAutorizacao4",
    },
    "PA": {
        "autorizacao_producao":    "https://nfce.sefa.pa.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfce.sefa.pa.gov.br/nfce/services/NFeAutorizacao4",
    },
    "PB": {
        "autorizacao_producao":    "https://nfce.sefaz.pb.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfce.sefaz.pb.gov.br/nfce/services/NFeAutorizacao4",
    },
    "PE": {
        "autorizacao_producao":    "https://nfce.sefaz.pe.gov.br/nfce-service/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfcehomolog.sefaz.pe.gov.br/nfce-service/services/NFeAutorizacao4",
    },
    "PI": {
        "autorizacao_producao":    "https://www.sefaz.pi.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://www.sefaz.pi.gov.br/nfce/services/NFeAutorizacao4",
    },
    "PR": {
        "autorizacao_producao":    "https://nfce.sefa.pr.gov.br/ws/NFeAutorizacao4",
        "autorizacao_homologacao": "https://homologacao.sefa.pr.gov.br/ws/NFeAutorizacao4",
    },
    "RJ": {
        "autorizacao_producao":    "https://nfce.fazenda.rj.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://homologacao.nfce.fazenda.rj.gov.br/nfce/services/NFeAutorizacao4",
    },
    "RN": {
        "autorizacao_producao":    "https://nfce.set.rn.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://hom.nfce.set.rn.gov.br/nfce/services/NFeAutorizacao4",
    },
    "RO": {
        "autorizacao_producao":    "https://nfce.sefin.ro.gov.br/ws/NFeAutorizacao4",
        "autorizacao_homologacao": "https://nfce.sefin.ro.gov.br/ws/NFeAutorizacao4",
    },
    "RR": {
        "autorizacao_producao":    "https://sefaz.rr.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://sefaz.rr.gov.br/nfce/services/NFeAutorizacao4",
    },
    "RS": {
        "autorizacao_producao":    "https://nfce.sefaz.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://nfce-homologacao.sefaz.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
    },
    "SC": {
        # SC usa SVRS
        "autorizacao_producao":    "https://nfce.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
    },
    "SE": {
        "autorizacao_producao":    "https://www.nfce.se.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://www.hom.nfce.se.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
    },
    "SP": {
        "autorizacao_producao":    "https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
        "autorizacao_homologacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
    },
    "TO": {
        "autorizacao_producao":    "https://nfce.sefaz.to.gov.br/nfce/services/NFeAutorizacao4",
        "autorizacao_homologacao": "https://homologacao.sefaz.to.gov.br/nfce/services/NFeAutorizacao4",
    },
}
