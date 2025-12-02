from django import forms
from Licencas.models import Usuarios
from OrdemdeServico.models import OrdemServicoFaseSetor
import logging
logger = logging.getLogger(__name__)


class FilialCertificadoForm(forms.Form):
    certificado = forms.FileField()
    senha = forms.CharField(widget=forms.PasswordInput())
    empresa_id = forms.IntegerField(widget=forms.HiddenInput())
    filial_id = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # Garantir classes bootstrap
            if name == 'certificado' and not isinstance(field.widget, forms.ClearableFileInput):
                field.widget = forms.ClearableFileInput()
            if name == 'senha' and not isinstance(field.widget, forms.PasswordInput):
                field.widget = forms.PasswordInput()
            css = field.widget.attrs.get('class', '')
            if name == 'certificado':
                field.widget.attrs['class'] = (css + ' form-control-file').strip()
            elif name == 'senha':
                field.widget.attrs['class'] = (css + ' form-control').strip()
            # Associar ao form separado de upload
            field.widget.attrs['form'] = 'certificadoUploadForm'

class EmpresaForm(forms.ModelForm):
    class Meta:
        from Licencas.models import Empresas
        model = Empresas
        fields = ['empr_codi','empr_nome','empr_docu']
        labels = {
            'empr_codi': 'Código',
            'empr_nome': 'Nome da Empresa',
            'empr_docu': 'CNPJ',
        }
        widgets = {
            'empr_codi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código da empresa'}),
            'empr_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'empr_docu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNPJ'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'empr_codi' in self.fields:
            self.fields['empr_codi'].required = False
            self.fields['empr_codi'].widget.attrs.setdefault('readonly', 'readonly')
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.setdefault('class', 'form-control')
            if self.is_bound and self.errors.get(name):
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (css + ' is-invalid').strip()

class FilialForm(forms.ModelForm):
    certificado = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}))
    senha_certificado = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    class Meta:
        from Licencas.models import Filiais
        model = Filiais
        exclude = ['empr_empr','empr_codi']
        labels = {
            'empr_docu': 'CNPJ da Filial',
            'empr_insc_esta': 'Inscrição Estadual',
            'empr_insc_muni': 'Inscrição Municipal',
            'empr_fant': 'Nome Fantasia',
            'empr_sufr': 'SUFRAMA',
            'empr_cei': 'CEI',
            'empr_nire': 'NIRE',
            'empr_data_nire': 'Data do NIRE',
            'empr_cnae': 'CNAE',
            'empr_cae': 'CAE',
            'empr_natu_juri': 'Natureza Jurídica',
            'empr_regi': 'Registro',
            'empr_regi_trib': 'Regime Tributário',
            'empr_data_regi': 'Data de Registro',
            'empr_regi_junt': 'Registro Junta',
            'empr_regi_outr': 'Outros Registros',
            'empr_cep': 'CEP',
            'empr_ende': 'Endereço',
            'empr_nume': 'Número',
            'empr_comp': 'Complemento',
            'empr_bair': 'Bairro',
            'empr_cida': 'Cidade',
            'empr_esta': 'UF',
            'empr_pais': 'País',
            'empr_fone': 'Telefone',
            'empr_resp': 'Responsável',
            'empr_celu': 'Celular',
            'empr_emai': 'Email',
            'empr_emai_empr': 'Email Empresarial',
            'empr_pagi': 'Página Web',
            'empr_obse': 'Observações',
            'empr_codi_cida': 'Código Cidade',
            'empr_codi_esta': 'Código Estado',
            'empr_codi_pais': 'Código País',
            'empr_ambi_nfe': 'Ambiente NF-e',
            'empr_smtp_host': 'SMTP Host',
            'empr_smtp_port': 'SMTP Porta',
            'empr_smtp_usua': 'SMTP Usuário',
            'empr_smtp_senh': 'SMTP Senha',
            'empr_smtp_emai': 'SMTP Email',
            'empr_cone_segu': 'Conexão Segura',
            'empr_ssl': 'SSL',
            'empr_tls': 'TLS',
            'empr_seri_cert_cte': 'Série Certificado CTe',
            'empr_senh_cert_cte': 'Senha Certificado CTe',
            'empr_ambi_cte': 'Ambiente CTe',
            'empr_cert_nfs': 'Certificado NFS-e',
            'empr_senh_cert_nfs': 'Senha Certificado NFS-e',
            'empr_rps': 'RPS',
            'empr_seri_nfes': 'Série NFS-e',
            'empr_regi_trib_serv': 'Regime Tributário Serviços',
            'empr_simp_naci_serv': 'Simples Nacional Serviços',
        }
        widgets = {
            'empr_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Filial'}),
            'empr_fant': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia'}),
            'empr_docu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNPJ da Filial'}),
            'empr_insc_esta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inscrição Estadual'}),
            'empr_insc_muni': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inscrição Municipal'}),
            'empr_sufr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SUFRAMA'}),
            'empr_cei': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CEI'}),
            'empr_nire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIRE'}),
            'empr_data_nire': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'empr_cnae': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNAE'}),
            'empr_cae': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CAE'}),
            'empr_natu_juri': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Natureza Jurídica'}),
            'empr_regi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registro'}),
            'empr_regi_trib': forms.Select(attrs={'class': 'form-select'}),
            'empr_data_regi': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'empr_regi_junt': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registro Junta'}),
            'empr_regi_outr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Outros Registros'}),
            'empr_teso': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CEP'}),
            'empr_ende': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Endereço'}),
            'empr_nume': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'empr_comp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Complemento'}),
            'empr_bair': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bairro'}),
            'empr_cida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade'}),
            'empr_esta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UF'}),
            'empr_pais': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'País'}),
            'empr_codi_cida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Cidade'}),
            'empr_codi_esta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Estado'}),
            'empr_codi_pais': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código País'}),
            'empr_fone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'empr_resp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Responsável'}),
            'empr_celu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Celular'}),
            'empr_emai': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'empr_emai_empr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Empresarial'}),
            'empr_pagi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Página Web'}),
            'empr_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações'}),
            'empr_seri_cert_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Série Certificado CT-e'}),
            'empr_senh_cert_cte': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha Certificado CT-e'}),
            'empr_ambi_cte': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_cert_nfs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Certificado NFS-e'}),
            'empr_senh_cert_nfs': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha Certificado NFS-e'}),
            'empr_rps': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_seri_nfes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Série NFS-e'}),
            'empr_regi_trib_serv': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_simp_naci_serv': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_smtp_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Host'}),
            'empr_smtp_port': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Porta'}),
            'empr_smtp_usua': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Usuário'}),
            'empr_smtp_senh': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Senha'}),
            'empr_smtp_emai': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Email'}),
            'empr_cone_segu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_smtp_host_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Host CT-e'}),
            'empr_smtp_port_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Porta CT-e'}),
            'empr_smtp_usua_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Usuário CT-e'}),
            'empr_smtp_senh_cte': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Senha CT-e'}),
            'empr_smtp_emai_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SMTP Email CT-e'}),
            'empr_cone_segu_cte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_ssl_cte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_tls_cte': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_prox_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Host'}),
            'empr_prox_port': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Porta'}),
            'empr_prox_usua': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Usuário'}),
            'empr_prox_senh': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Senha'}),
            'empr_prox_host_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Host CT-e'}),
            'empr_prox_port_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Porta CT-e'}),
            'empr_prox_user_cte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Usuário CT-e'}),
            'empr_prox_pass_cte': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Senha CT-e'}),
            'empr_prox_host_nfs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Host NFS-e'}),
            'empr_prox_port_nfs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Porta NFS-e'}),
            'empr_prox_usua_nfs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Usuário NFS-e'}),
            'empr_prox_senh_nfs': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Proxy Senha NFS-e'}),
            'empr_ambi_nfe': forms.Select(attrs={'class': 'form-control'}),    
            'empr_ambi_nfec': forms.Select(attrs={'class': 'form-control'}),
            'empr_lote_nfe': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_lote_even_nfe': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_mdf_nfe': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_cte_esta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_mdf_cte': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_ambi_nfe_nfs': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_temp_resp_nfs': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_codi_serv': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Serviço'}),
            'empr_exig_iss': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_perf_sped': forms.TextInput(attrs={'class': 'form-control'}),
            'empr_ativ_sped': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_apur_ipi': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_lote_cart_corr': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_nsu': forms.NumberInput(attrs={'class': 'form-control'}),
            'empr_danf_pais': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empr_senh_elot': forms.PasswordInput(attrs={'class': 'form-control'}),
            'empr_id_toke': forms.TextInput(attrs={'class': 'form-control'}),
            'empr_csn_toke': forms.TextInput(attrs={'class': 'form-control'}),
            'empr_tipo_empr_ecd': forms.TextInput(attrs={'class': 'form-control'}),
            'empr_cabe_empr': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'empr_desc_serv': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.TextInput):
                field.widget.attrs.setdefault('class', 'form-control')
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.setdefault('class', 'form-control')
                field.widget.attrs.setdefault('step', '1')
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs.setdefault('class', 'form-control')
                field.widget.attrs.setdefault('type', 'date')
            if isinstance(field.widget, forms.TimeInput):
                field.widget.attrs.setdefault('class', 'form-control')
                field.widget.attrs.setdefault('type', 'time')
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('class', 'form-control')
                field.widget.attrs.setdefault('rows', 3)
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            if self.is_bound and self.errors.get(name):
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (css + ' is-invalid').strip()


class UsuarioForm(forms.ModelForm):
    setor = forms.ModelChoiceField(
        queryset=OrdemServicoFaseSetor.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None,
        required=True,
    )
    class Meta:
        model = Usuarios
        fields = ['usua_codi', 'usua_nome', 'password', 'usua_seto']
        widgets = {
            'usua_codi': forms.HiddenInput(attrs={'class': 'form-control', 'placeholder': 'Código Usuário'}),
            'usua_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Usuário'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha Usuário'}),
            'usua_seto': forms.HiddenInput(),
        }
        labels = {
            'usua_codi': 'Código Usuário',
            'usua_nome': 'Nome Usuário',
            'password': 'Senha Usuário',
            'usua_seto': 'Setor Usuário',
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        try:
            if request:
                from core.registry import get_licenca_db_config
                banco = get_licenca_db_config(request)
                self.fields['setor'].queryset = OrdemServicoFaseSetor.objects.using(banco).all()
                logger.info('[UsuarioForm] queryset setor carregado do banco=%s', banco)
        except Exception:
            pass
        # usua_seto é preenchido via campo 'setor' e não deve ser requerido no POST
        if 'usua_seto' in self.fields:
            self.fields['usua_seto'].required = False
        inst = kwargs.get('instance') or getattr(self, 'instance', None)
        if inst and hasattr(inst, 'setor') and inst.setor:
            self.fields['setor'].initial = inst.setor
            logger.debug('[UsuarioForm] inicial setor=%s', inst.setor)
            # Em edição, senha pode ser opcional
            if 'password' in self.fields:
                self.fields['password'].required = False
        else:
            # Em criação, manter senha obrigatória
            if 'password' in self.fields:
                self.fields['password'].required = True
        for name, field in self.fields.items():
            if self.is_bound and self.errors.get(name):
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (css + ' is-invalid').strip()

    def clean(self):
        cleaned = super().clean()
        setor = cleaned.get('setor')
        if setor:
            cleaned['usua_seto'] = getattr(setor, 'osfs_codi', getattr(setor, 'pk', None))
            logger.info('[UsuarioForm] mapeado setor->usua_seto=%s', cleaned['usua_seto'])
        if not cleaned.get('usua_seto'):
            self.add_error('setor', 'Selecione o setor')
            logger.warning('[UsuarioForm] usua_seto ausente, erro no setor')
        return cleaned
