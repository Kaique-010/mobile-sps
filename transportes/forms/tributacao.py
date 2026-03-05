from django import forms
from transportes.models import Cte, RegraICMS
from Entidades.models import Entidades
from Licencas.models import Filiais
from CFOP.models import CFOP
from transportes.services.icms_service import ICMSCalculationService
from transportes.services.st_service import STService
from transportes.services.difal_service import DIFALService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class CteTributacaoForm(forms.ModelForm):
    cfop = forms.ModelChoiceField(
        queryset=CFOP.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='CFOP'
    )

    class Meta:
        model = Cte
        fields = [
            'cfop', 'cst_icms', 'aliq_icms', 'base_icms', 'reducao_icms', 'valor_icms',
            'base_icms_st', 'aliquota_icms_st', 'valor_icms_st', 'margem_valor_adicionado_st', 'reducao_base_icms_st',
            'valor_bc_uf_dest', 'valor_icms_uf_dest', 'aliquota_interna_dest', 'aliquota_interestadual',
            'cst_pis', 'aliquota_pis', 'base_pis', 'valor_pis',
            'cst_cofins', 'aliquota_cofins', 'base_cofins', 'valor_cofins',
            # IBS e CBS
            'ibscbs_vbc', 'ibscbs_cstid', 'ibscbs_cst', 'ibscbs_cclasstrib',
            'ibs_pdifuf', 'ibs_vdifuf', 'ibs_vdevtribuf', 'ibs_vdevtribmun',
            'cbs_vdevtrib', 'ibs_pibsuf', 'ibs_preduf', 'ibs_paliqefetuf',
            'ibs_vibsuf', 'ibs_pdifmun', 'ibs_vdifmun', 'ibs_pibsmun',
            'ibs_predmun', 'ibs_paliqefetmun', 'ibs_vibsmun', 'ibs_vibs',
            'cbs_pdif', 'cbs_vdif', 'cbs_pcbs', 'cbs_pred', 'cbs_paliqefet',
            'cbs_vcbs', 'ibscbs_cstregid', 'ibscbs_cstreg', 'ibscbs_cclasstribreg',
            'ibs_paliqefetufreg', 'ibs_vtribufreg'
        ]
        widgets = {
            #'cfop': forms.NumberInput(attrs={'class': 'form-control'}), # Removido, tratado no init
            'cst_icms': forms.TextInput(attrs={'class': 'form-control'}),
            'aliq_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_icms': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            
            'base_icms_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_icms_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_icms_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'margem_valor_adicionado_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reducao_base_icms_st': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            
            'valor_bc_uf_dest': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_icms_uf_dest': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_interna_dest': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_interestadual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),

            'cst_pis': forms.TextInput(attrs={'class': 'form-control'}),
            'aliquota_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_pis': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cst_cofins': forms.TextInput(attrs={'class': 'form-control'}),
            'aliquota_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_cofins': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            # IBS e CBS Widgets (simplified)
            'ibscbs_vbc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ibscbs_cst': forms.TextInput(attrs={'class': 'form-control'}),
            'ibscbs_cclasstrib': forms.TextInput(attrs={'class': 'form-control'}),
            'ibs_pibsuf': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ibs_vibsuf': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cbs_pcbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cbs_vcbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        db_alias = 'default'
        if self.instance and self.instance.pk:
            db_alias = self.instance._state.db or 'default'
        
        # Se tiver request, usa o db do request que é mais garantido para multi-tenant via rota
        if self.request:
             from core.utils import get_licenca_db_config
             db_alias = get_licenca_db_config(self.request)
        
        # Configura queryset do CFOP
        self.fields['cfop'].queryset = CFOP.objects.using(db_alias).all().order_by('cfop_codi')
        
        # Configura valor inicial do CFOP se existir no model (que é IntegerField)
        if self.instance and self.instance.pk and self.instance.cfop:
            try:
                # Tenta encontrar o objeto CFOP correspondente ao código gravado (ex: 5102)
                # O campo cfop do Cte é Integer, mas cfop_codi no CFOP é CharField
                cfop_codi_str = str(self.instance.cfop)
                # Padding com zeros se necessário? Normalmente não, é gravado como inteiro.
                # Mas o CFOP.cfop_codi é char(10). Pode ser "5102" ou "05102"?
                # Geralmente "5102".
                cfop_obj = CFOP.objects.using(db_alias).filter(cfop_codi=cfop_codi_str).first()
                if cfop_obj:
                    self.initial['cfop'] = cfop_obj
            except Exception as e:
                logger.warning(f"Erro ao carregar CFOP inicial: {e}")

    def clean_cfop(self):
        cfop_obj = self.cleaned_data.get('cfop')
        if cfop_obj:
            # Retorna apenas o código numérico para salvar no campo IntegerField do model Cte
            try:
                return int(cfop_obj.cfop_codi)
            except (ValueError, TypeError):
                return None
        return None

    def clean(self):
        cleaned_data = super().clean()
        
        if self.errors:
            return cleaned_data
            
        instance = self.instance
        # Garante uso do banco correto
        db_alias = instance._state.db or 'default'
        
        cfop_val = cleaned_data.get('cfop')
        
        if not cfop_val:
            return cleaned_data
            
        try:
            # Busca configuração do CFOP
            # Tenta encontrar por código e empresa primeiro
            cfop_obj = CFOP.objects.using(db_alias).filter(
                cfop_codi=str(cfop_val),
                cfop_empr=instance.empresa
            ).first()
            
            # Se não encontrar, tenta genérico
            if not cfop_obj:
                 cfop_obj = CFOP.objects.using(db_alias).filter(
                    cfop_codi=str(cfop_val)
                ).first()
                
            if not cfop_obj:
                return cleaned_data

            # Base de Cálculo
            base_icms = cleaned_data.get('base_icms')
            
            # Se base não informada, usa valor total do serviço
            if not base_icms:
                 valor_total = instance.total_valor or Decimal('0.00')
                 base_icms = valor_total
                 cleaned_data['base_icms'] = base_icms
            
            # Verifica entidades para UFs
            remetente_id = instance.remetente
            destinatario_id = instance.destinatario
            
            if not remetente_id or not destinatario_id:
                # Sem participantes não dá para definir regras de UF
                return cleaned_data
                
            remetente = Entidades.objects.using(db_alias).filter(pk=remetente_id).first()
            destinatario = Entidades.objects.using(db_alias).filter(pk=destinatario_id).first()
            
            if not remetente or not destinatario:
                return cleaned_data

            filial_id = instance.filial
            filial = Filiais.objects.using(db_alias).filter(pk=filial_id).first()
            
            if not filial:
                return cleaned_data
            
            # Regime Tributário (1 = Simples Nacional)
            # Licencas/models.py: empr_regi_trib
            simples_nacional = str(filial.empr_regi_trib) == '1'
            
            # UFs (Simplificação: Origem=Remetente, Destino=Destinatário)
            uf_origem = remetente.enti_esta
            uf_destino = destinatario.enti_esta
            
            # Contribuinte (Se tem IE e não é isento)
            ie_dest = destinatario.enti_insc_esta
            contribuinte = bool(ie_dest and ie_dest.strip().upper() not in ['ISENTO', 'ISENTA', ''])
            
            # Adaptadores para os Services
            class ServiceEmpresaAdapter:
                def __init__(self, simples, db_alias='default'):
                    self.simples_nacional = simples
                    self._state = type('State', (), {'db': db_alias})
            
            class ServiceOperacaoAdapter:
                def __init__(self, uf_orig, uf_dest, contrib):
                    self.uf_origem = uf_orig
                    self.uf_destino = uf_dest
                    self.contribuinte = contrib
            
            empresa_adapter = ServiceEmpresaAdapter(simples_nacional, db_alias)
            operacao_adapter = ServiceOperacaoAdapter(uf_origem, uf_destino, contribuinte)
            
            # --- Cálculo ICMS ---
            icms_calculado_valor = Decimal('0.00')
            if cfop_obj.cfop_exig_icms:
                icms_service = ICMSCalculationService(empresa_adapter, operacao_adapter)
                res_icms = icms_service.calcular(base_icms, cfop_obj)
                
                if res_icms:
                    cleaned_data['cst_icms'] = res_icms['cst']
                    cleaned_data['aliq_icms'] = res_icms['aliquota']
                    cleaned_data['valor_icms'] = res_icms['valor']
                    cleaned_data['reducao_icms'] = res_icms['reducao']
                    cleaned_data['base_icms'] = res_icms['base'] # Base reduzida
                    icms_calculado_valor = res_icms['valor']
            
            # --- Cálculo ST ---
            if cfop_obj.cfop_gera_st:
                st_service = STService(empresa_adapter, operacao_adapter)
                res_st = st_service.calcular(base_icms, icms_calculado_valor, cfop_obj)
                
                if res_st:
                    cleaned_data['base_icms_st'] = res_st['base_st']
                    cleaned_data['valor_icms_st'] = res_st['valor_st']
                    cleaned_data['aliquota_icms_st'] = res_st['aliquota_st']
                    cleaned_data['margem_valor_adicionado_st'] = res_st['mva_st']
                
            # --- Cálculo DIFAL ---
            if cfop_obj.cfop_gera_difal:
                difal_service = DIFALService(empresa_adapter, operacao_adapter)
                # DIFAL usa a base original ou reduzida? Geralmente base original, mas o service recebe 'base_calculo'.
                # Vamos passar a base original (sem redução ICMS próprio) se houver, ou a base calculada?
                # Service DIFAL usa base passada.
                # Geralmente DIFAL é sobre o valor da operação.
                res_difal = difal_service.calcular(base_icms, icms_calculado_valor, cfop_obj)
                
                if res_difal:
                    cleaned_data['valor_bc_uf_dest'] = res_difal['base_difal']
                    cleaned_data['valor_icms_uf_dest'] = res_difal['valor_difal']
                    cleaned_data['aliquota_interestadual'] = res_difal['aliquota_interestadual']
                    cleaned_data['aliquota_interna_dest'] = res_difal['aliquota_destino']
                
        except Exception as e:
            logger.error(f"Erro ao calcular impostos no CteTributacaoForm: {e}")
            
        return cleaned_data
