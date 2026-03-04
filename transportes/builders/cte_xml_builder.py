import logging
from datetime import datetime
import re
import random

# Tenta importar pytrustnfe, mas não quebra se não estiver instalado (para testes)
try:
    from pytrustnfe.cte import CTe
    from pytrustnfe.cte.dados import (
        InfCte, Ide, Emit, Rem, Dest, VPrest, Comp, Imp, ICMS, 
        InfCTeNorm, InfModal, Rodo, Moto, Veic, InfNF, InfOutros, AutXML,
        Exped, Receb, Tomador03, Tomador04, EnderEmit, EnderReme, EnderDest, EnderToma,
        InfCarga, InfDoc, InfQ, InfNFe
    )
except ImportError:
    # Classes Mock para permitir execução sem a lib instalada
    class CTe: 
        def __init__(self, **kwargs): pass
        def xml(self): return "<CTe>XML Mock</CTe>"
    class InfCte: 
        def __init__(self, **kwargs): pass
    class Ide: 
        def __init__(self, **kwargs): pass
    class Emit: 
        def __init__(self, **kwargs): pass
    class Rem: 
        def __init__(self, **kwargs): pass
    class Dest: 
        def __init__(self, **kwargs): pass
    class VPrest: 
        def __init__(self, **kwargs): pass
    class Comp: 
        def __init__(self, **kwargs): pass
    class Imp: 
        def __init__(self, **kwargs): pass
    class ICMS: 
        def __init__(self, **kwargs): pass
    class InfCTeNorm: 
        def __init__(self, **kwargs): pass
    class InfModal: 
        def __init__(self, **kwargs): pass
    class Rodo: 
        def __init__(self, **kwargs): pass
    class Moto: 
        def __init__(self, **kwargs): pass
    class Veic: 
        def __init__(self, **kwargs): pass
    class InfNF: 
        def __init__(self, **kwargs): pass
    class InfOutros: 
        def __init__(self, **kwargs): pass
    class AutXML: 
        def __init__(self, **kwargs): pass
    class Exped: 
        def __init__(self, **kwargs): pass
    class Receb: 
        def __init__(self, **kwargs): pass
    class Tomador03: 
        def __init__(self, **kwargs): pass
    class Tomador04: 
        def __init__(self, **kwargs): pass
    class EnderEmit: 
        def __init__(self, **kwargs): pass
    class EnderReme: 
        def __init__(self, **kwargs): pass
    class EnderDest: 
        def __init__(self, **kwargs): pass
    class EnderToma: 
        def __init__(self, **kwargs): pass
    class InfCarga: 
        def __init__(self, **kwargs): pass
    class InfDoc: 
        def __init__(self, **kwargs): pass
    class InfQ: 
        def __init__(self, **kwargs): pass
    class InfNFe:
        def __init__(self, **kwargs): pass

from transportes.models import Cte, CteDocumento
from Entidades.models import Entidades
from Licencas.models import Filiais

logger = logging.getLogger(__name__)

class CteXmlBuilder:
    def __init__(self, cte: Cte):
        self.cte = cte
        self.filial = None
        self.remetente = None
        self.destinatario = None
        self.expedidor = None
        self.recebedor = None
        self.tomador = None
        
        self._carregar_dados()

    def _carregar_dados(self):
        """Carrega os dados relacionados necessários para o XML"""
        # Carregar dados da filial emitente
        try:
            self.filial = Filiais.objects.defer('empr_cert_digi').filter(
                empr_empr=self.cte.empresa,
                empr_codi=self.cte.filial
            ).first()
            if not self.filial:
                 raise Exception("Filial não encontrada.")
        except Exception as e:
            logger.error(f"Erro ao carregar dados da filial: {e}")
            raise Exception("Dados da filial emitente não encontrados.")

        # Carregar dados das entidades envolvidas
        if self.cte.remetente:
            self.remetente = Entidades.objects.filter(enti_clie=self.cte.remetente).first()
        
        if self.cte.destinatario:
            self.destinatario = Entidades.objects.filter(enti_clie=self.cte.destinatario).first()
            
        # Carregar outros envolvidos se houver (expedidor, recebedor, tomador se for outro)
        if self.cte.tomador_servico == 4 and self.cte.outro_tomador:
            self.tomador = Entidades.objects.filter(enti_clie=self.cte.outro_tomador).first()

    def build(self) -> str:
        """Constrói o objeto CTe e retorna o XML assinado (ou apenas gerado)"""
        
        # 1. Identificação
        ide = self._build_ide()
        
        # 2. Emitente
        emit = self._build_emit()
        
        # 3. Remetente
        rem = self._build_rem()
        
        # 4. Destinatário
        dest = self._build_dest()
        
        # 5. Valores da Prestação
        vprest = self._build_vprest()
        
        # 6. Impostos
        imp = self._build_imp()
        
        # 7. Informações do Modal e Carga
        inf_cte_norm = self._build_inf_cte_norm()
        
        # 8. Tomador (se for 3 ou 4)
        toma3 = None
        toma4 = None
        if self.cte.tomador_servico == 3: 
             # Tomador é o destinatário (3)
             toma3 = Tomador03(toma=self.cte.tomador_servico)
        elif self.cte.tomador_servico == 4:
            toma4 = self._build_toma4()
        elif self.cte.tomador_servico in [0, 1, 2]:
             toma3 = Tomador03(toma=self.cte.tomador_servico)

        # Monta o InfCte
        chave = self._gerar_chave_acesso()
        self.cte.chave_de_acesso = chave # Salva a chave gerada no objeto CTe (não salva no banco ainda)
        
        inf_cte = InfCte(
            versao="3.00", 
            Id=f"CTe{chave}",
            ide=ide,
            emit=emit,
            rem=rem,
            dest=dest,
            vPrest=vprest,
            imp=imp,
            infCTeNorm=inf_cte_norm,
            toma3=toma3,
            toma4=toma4
        )
        
        # Cria o objeto CTe
        cte_obj = CTe(infCTe=inf_cte)
        
        if hasattr(cte_obj, 'xml'):
             return cte_obj.xml()
        else:
             return "<CTe>XML Gerado</CTe>"

    def _gerar_chave_acesso(self):
        # Se já tiver chave válida (44 digitos), usa ela
        if self.cte.chave_de_acesso and len(self.cte.chave_de_acesso) == 44:
            return self.cte.chave_de_acesso
            
        # Geração de chave de acesso real
        # UF(2) + AM(2) + CNPJ(14) + MOD(2) + SERIE(3) + NUM(9) + TPEMIS(1) + CDV(8)
        
        uf = str(getattr(self.filial, 'empr_codi_uf', '35')).zfill(2)
        agora = datetime.now()
        am = f"{agora.year % 100:02d}{agora.month:02d}"
        cnpj = self._limpar_numero(self.filial.empr_docu).zfill(14)
        mod = (self.cte.modelo or "57").zfill(2)
        serie = str(self.cte.serie or "1").zfill(3)
        nct = str(self.cte.numero).zfill(9)
        tp_emis = str(self.cte.forma_emissao or "1")
        
        # Código numérico aleatório (8 dígitos)
        cct = f"{random.randint(0, 99999999):08d}"
        
        chave_sem_dv = f"{uf}{am}{cnpj}{mod}{serie}{nct}{tp_emis}{cct}"
        
        # Cálculo do DV (módulo 11)
        soma = 0
        peso = 2
        for digito in reversed(chave_sem_dv):
            soma += int(digito) * peso
            peso += 1
            if peso > 9:
                peso = 2
        
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        
        return f"{chave_sem_dv}{dv}"

    def _build_ide(self):
        return Ide(
            cUF=str(getattr(self.filial, 'empr_codi_uf', '35')), 
            cCT=str(self.cte.numero).zfill(8), # Usando numero como cCT por simplicidade, ou random
            CFOP=str(self.cte.cfop or "5353"),
            natOp="PRESTACAO DE SERVICO", 
            mod=self.cte.modelo or "57",
            serie=str(self.cte.serie or "1"),
            nCT=str(self.cte.numero),
            dhEmi=datetime.now().isoformat(),
            tpImp="1", 
            tpEmis=self.cte.forma_emissao or "1", 
            cDV="0", # Será calculado na chave
            tpAmb=self.filial.empr_ambi_cte or "2", 
            tpCTe=self.cte.tipo_cte or "0", 
            procEmi="0", 
            verProc="1.0",
            cMunEnv=str(getattr(self.filial, 'empr_codi_cida', '0000000')), 
            xMunEnv=self.filial.empr_cida or "Cidade",
            UFEnv=self.filial.empr_esta or "UF",
            modal="01", # 01-Rodoviário
            tpServ=self.cte.tipo_servico or "0", 
            indIEToma="1", 
            cMunIni=str(self.cte.cidade_coleta), 
            xMunIni="Cidade Inicio", 
            UFIni="UF", 
            cMunFim=str(self.cte.cidade_entrega), 
            xMunFim="Cidade Fim",
            UFFim="UF", 
            retira="1", 
            xDetRetira="" 
        )

    def _limpar_numero(self, valor):
        if not valor: return ""
        return re.sub(r'\D', '', str(valor))

    def _build_emit(self):
        if not self.filial:
            return None
            
        cnpj = self._limpar_numero(self.filial.empr_docu)
        
        ender = EnderEmit(
            xLgr=self.filial.empr_ende or "",
            nro=self.filial.empr_nume or "S/N",
            xCpl=self.filial.empr_comp or "",
            xBairro=self.filial.empr_bair or "",
            cMun=str(getattr(self.filial, 'empr_codi_cida', '')),
            xMun=self.filial.empr_cida or "",
            UF=self.filial.empr_esta or "",
            CEP=self._limpar_numero(self.filial.empr_cep),
            fone=self._limpar_numero(self.filial.empr_fone)
        )
            
        return Emit(
            CNPJ=cnpj,
            IE=self._limpar_numero(self.filial.empr_insc_esta),
            xNome=self.filial.empr_nome,
            xFant=self.filial.empr_fant or self.filial.empr_nome,
            enderEmit=ender
        )

    def _build_rem(self):
        if not self.remetente:
            return None
            
        cnpj = self._limpar_numero(self.remetente.enti_cnpj)
        cpf = self._limpar_numero(self.remetente.enti_cpf)
        
        ender = EnderReme(
             xLgr=self.remetente.enti_ende or "",
             nro=self.remetente.enti_nume or "S/N",
             xCpl=self.remetente.enti_comp or "",
             xBairro=self.remetente.enti_bair or "",
             cMun=str(getattr(self.remetente, 'enti_cida_codi', '') or ''),
             xMun=self.remetente.enti_cida or "",
             UF=self.remetente.enti_esta or "",
             CEP=self._limpar_numero(self.remetente.enti_cep),
             fone=self._limpar_numero(self.remetente.enti_fone) if hasattr(self.remetente, 'enti_fone') else ""
        )
        
        return Rem(
            CNPJ=cnpj if cnpj else None,
            CPF=cpf if cpf and not cnpj else None,
            IE=self._limpar_numero(self.remetente.enti_insc_esta),
            xNome=self.remetente.enti_nome,
            enderReme=ender
        )

    def _build_dest(self):
        if not self.destinatario:
            return None
            
        cnpj = self._limpar_numero(self.destinatario.enti_cnpj)
        cpf = self._limpar_numero(self.destinatario.enti_cpf)
        
        ender = EnderDest(
             xLgr=self.destinatario.enti_ende or "",
             nro=self.destinatario.enti_nume or "S/N",
             xCpl=self.destinatario.enti_comp or "",
             xBairro=self.destinatario.enti_bair or "",
             cMun=str(getattr(self.destinatario, 'enti_cida_codi', '') or ''),
             xMun=self.destinatario.enti_cida or "",
             UF=self.destinatario.enti_esta or "",
             CEP=self._limpar_numero(self.destinatario.enti_cep),
             fone=self._limpar_numero(self.destinatario.enti_fone) if hasattr(self.destinatario, 'enti_fone') else ""
        )
        
        return Dest(
            CNPJ=cnpj if cnpj else None,
            CPF=cpf if cpf and not cnpj else None,
            IE=self._limpar_numero(self.destinatario.enti_insc_esta),
            xNome=self.destinatario.enti_nome,
            enderDest=ender
        )

    def _build_vprest(self):
        # pytrustnfe espera valores como string formatada '0.00'
        def fmt(v): return "{:.2f}".format(float(v or 0))
        
        comps = []
        if self.cte.frete_valor:
             comps.append(Comp(xNome="Frete Valor", vComp=fmt(self.cte.frete_valor)))
        if self.cte.pedagio:
             comps.append(Comp(xNome="Pedagio", vComp=fmt(self.cte.pedagio)))
        
        # Se não tiver componentes, adiciona um genérico
        if not comps:
             comps.append(Comp(xNome="Frete Peso", vComp=fmt(self.cte.total_valor)))

        return VPrest(
            vTPrest=fmt(self.cte.total_valor),
            vRec=fmt(self.cte.liquido_a_receber),
            Comp=comps
        )

    def _build_imp(self):
        def fmt(v): return "{:.2f}".format(float(v or 0))
        
        # ICMS00 - Tributado Integralmente
        icms = ICMS(
            CST=self.cte.cst_icms or "00",
            vBC=fmt(self.cte.base_icms),
            pICMS=fmt(self.cte.aliq_icms),
            vICMS=fmt(self.cte.valor_icms)
        )
        # Poderia ter lógica para outros CSTs (20, 40, 60, 90, SN) aqui
        
        return Imp(ICMS=icms)

    def _build_inf_cte_norm(self):
        rodo = Rodo(
            RNTRC=self.cte.rntrc if hasattr(self.cte, 'rntrc') else '00000000',
        )
        
        inf_carga = self._build_inf_carga()
        inf_doc = self._build_inf_doc()
        
        return InfCTeNorm(
            infCarga=inf_carga,
            infDoc=inf_doc, 
            infModal=InfModal(versaoModal="3.00", rodo=rodo)
        )

    def _build_inf_carga(self):
        def fmt(v): return "{:.4f}".format(float(v or 0))
        def fmt_val(v): return "{:.2f}".format(float(v or 0))

        # Mapeamento de unidade de medida
        # 00-M3, 01-KG, 02-TON, 03-UNIDADE, 04-LITROS, 05-MMBTU
        unid_map = {
            'M3': '00', 'KG': '01', 'TN': '02', 'TONELADA': '02', 
            'UN': '03', 'LITRO': '04', 'LITROS': '04'
        }
        c_unid = unid_map.get(str(self.cte.tipo_medida).upper(), '01')
        
        inf_q_list = []
        
        # Peso Total (KG)
        if self.cte.peso_total:
             inf_q_list.append(InfQ(
                 cUnid='01', # KG
                 tpMed='PESO BRUTO',
                 qCarga=fmt(self.cte.peso_total)
             ))
        
        # Se não tiver peso, usa 0
        if not inf_q_list:
             inf_q_list.append(InfQ(cUnid='01', tpMed='PESO BRUTO', qCarga='0.0000'))

        return InfCarga(
            vCarga=fmt_val(self.cte.total_mercadoria),
            proPred=self.cte.produto_predominante or "DIVERSOS",
            infQ=inf_q_list
        )

    def _build_inf_doc(self):
        # Itera sobre CteDocumento
        docs = self.cte.documentos.all()
        inf_nf = []
        
        for doc in docs:
            if doc.chave_nfe:
                inf_nf.append(InfNFe(chave=doc.chave_nfe))
                
        if inf_nf:
            return InfDoc(infNFe=inf_nf)
        return None

    def _build_toma4(self):
        if not self.tomador:
            return None
            
        cnpj = self._limpar_numero(self.tomador.enti_cnpj)
        cpf = self._limpar_numero(self.tomador.enti_cpf)
        
        ender = EnderToma(
             xLgr=self.tomador.enti_ende or "",
             nro=self.tomador.enti_nume or "S/N",
             xCpl=self.tomador.enti_comp or "",
             xBairro=self.tomador.enti_bair or "",
             cMun=str(getattr(self.tomador, 'enti_cida_codi', '') or ''),
             xMun=self.tomador.enti_cida or "",
             UF=self.tomador.enti_esta or "",
             CEP=self._limpar_numero(self.tomador.enti_cep),
             fone=self._limpar_numero(self.tomador.enti_fone) if hasattr(self.tomador, 'enti_fone') else ""
        )

        return Tomador04(
            toma="4",
            CNPJ=cnpj if cnpj else None,
            CPF=cpf if cpf and not cnpj else None,
            IE=self._limpar_numero(self.tomador.enti_insc_esta),
            xNome=self.tomador.enti_nome,
            enderToma=ender
        )
