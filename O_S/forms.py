from django import forms
import logging
from django.forms import inlineformset_factory
from .models import Os, PecasOs, ServicosOs
from OrdemdeServico.models import OrdemServicoFaseSetor
from Produtos.models import Produtos
from Entidades.models import Entidades

class SetorForm(forms.ModelForm):
    class Meta:
        model = OrdemServicoFaseSetor
        fields = [
            'osfs_codi',
            'osfs_nome',
        ]
        labels = {
            'osfs_codi': 'Código',
            'osfs_nome': 'Nome',
        }

class OsForm(forms.ModelForm):
    os_topr = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'readonly': True}))

    class Meta:
        model = Os
        fields = [
            'os_clie',
            'os_data_aber',
            'os_data_fech',
            'os_hora_aber',
            'os_tota',
            'os_fina_os',
            'os_resp',
            'os_desc',
            'os_stat_os',
            'os_situ',
            'os_seto',
        ]
        widgets = {
            'os_clie': forms.HiddenInput(),
            'os_data_aber': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'os_data_fech': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'os_hora_aber': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'os_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'readonly': True}),
            'os_fina_os': forms.Select(attrs={'class': 'form-select'}),
            'os_stat_os': forms.Select(attrs={'class': 'form-select'}),
            'os_resp': forms.HiddenInput(),
            'os_situ': forms.Select(attrs={'class': 'form-select'}),
            'os_desc': forms.NumberInput(attrs={'class': 'form-control','placeholder': '0.00', 'step': '0.01'}),
            'os_seto': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'os_clie': 'Cliente',
            'os_data_aber': 'Data Abertura',
            'os_data_fech': 'Data Fechamento',
            'os_hora_aber': 'Hora Abertura',
            'os_hora_fech': 'Hora Fechamento',
            'os_tota': 'Total',
            'os_fina_os': 'Tipo Financeiro',
            'os_resp': 'Responsável',
            'os_desc': 'Desconto',
            'os_seto': 'Setor',
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)

        super().__init__(*args, **kwargs)

        try:
            clientes_qs = Entidades.objects.using(database).filter(
                enti_tipo_enti__icontains='CL'
            )
            if empresa_id:
                clientes_qs = clientes_qs.filter(enti_empr=str(empresa_id))

            self.fields['os_clie'].queryset = clientes_qs.order_by('enti_nome')
            self.fields['os_clie'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
            self.fields['os_clie'].empty_label = "Selecione um cliente"
        except Exception as e:
            print(f"Erro ao carregar clientes: {e}")
            self.fields['os_clie'].queryset = Entidades.objects.none()

        try:
            vendedores_qs = Entidades.objects.using(database).filter(
                enti_tipo_enti__icontains='VE'
            )
            if empresa_id:
                vendedores_qs = vendedores_qs.filter(enti_empr=str(empresa_id))

            self.fields['os_resp'].queryset = vendedores_qs.order_by('enti_nome')
            self.fields['os_resp'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
            self.fields['os_resp'].empty_label = "Selecione o responsável"
        except Exception as e:
            print(f"Erro ao carregar responsáveis: {e}")
            self.fields['os_resp'].queryset = Entidades.objects.none()

        self.fields['os_fina_os'].choices = [
            (99, 'SEM FINANCEIRO'),
            (00, 'DUPLICATA'),
            (1, 'CHEQUE'),
            (2, 'PROMISSÓRIA'),
            (3, 'RECIBO'),
            (50, 'CHEQUE-PRÉ'),
            (51, 'CARTÃO DE CRÉDITO'),
            (52, 'CARTÃO DE DÉBITO'),
            (53, 'BOLETO'),
            (54, 'DINHEIRO'),
            (55, 'DEPÓSITO EM CONTA'),
            (60, 'PIX')
        ]
        
        self.fields['os_stat_os'].choices = [
            ('', 'Selecione o status'),
            ('0', 'Aberto'),
            ('1', 'Fechado'),
        ]
        self.fields['os_situ'].choices = [
            ('', 'Selecione a situação'),
            ('0', 'Ativo'),
            ('1', 'Inativo'),
        ]

        try:
            setores = OrdemServicoFaseSetor.objects.using(database).order_by('osfs_nome')
            self.fields['os_seto'].choices = [(s.osfs_codi, s.osfs_nome) for s in setores]
        except Exception:
            self.fields['os_seto'].choices = [('', 'Selecione o setor')]

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[OsForm.clean] os_desc=%s os_topr=%s os_tota=%s os_fina_os=%s os_stat_os=%s os_situ=%s os_seto=%s",
            cleaned.get('os_desc'), cleaned.get('os_topr'), cleaned.get('os_tota'), cleaned.get('os_fina_os'), cleaned.get('os_stat_os'), cleaned.get('os_situ'), cleaned.get('os_seto')
        )
        return cleaned


class PecasOsForm(forms.ModelForm):
    class Meta:
        model = PecasOs
        fields = ['peca_prod', 'peca_quan', 'peca_unit', 'peca_desc', 'peca_tota']
        widgets = {
            'peca_prod': forms.HiddenInput(),
            'peca_quan': forms.NumberInput(attrs={'class': 'form-control text-end', 'min': '1', 'value': '1'}),
            'peca_unit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
            'peca_desc': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
            'peca_tota': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00', 'readonly': True}),
        }
        labels = {
            'peca_prod': 'Produto',
            'peca_quan': 'Quantidade',
            'peca_unit': 'Preço Unitário',
            'peca_desc': 'Desconto',
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)

        super().__init__(*args, **kwargs)

        try:
            produtos_qs = Produtos.objects.using(database).all()
            if empresa_id:
                produtos_qs = produtos_qs.filter(prod_empr=str(empresa_id))
            self.produtos = produtos_qs.order_by('prod_nome')[:500]
        except Exception as e:
            print(f"Erro ao carregar produtos: {e}")
            self.produtos = Produtos.objects.none()

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[PecasOsForm.clean] peca_prod=%s peca_quan=%s peca_unit=%s peca_desc=%s",
            cleaned.get('peca_prod'), cleaned.get('peca_quan'), cleaned.get('peca_unit'), cleaned.get('peca_desc')
        )
        return cleaned


class ServicosOsForm(forms.ModelForm):
    class Meta:
        model = ServicosOs
        fields = ['serv_prod', 'serv_quan', 'serv_unit', 'serv_desc', 'serv_tota']
        widgets = {
            'serv_prod': forms.HiddenInput(),
            'serv_quan': forms.NumberInput(attrs={'class': 'form-control text-end', 'min': '1', 'value': '1'}),
            'serv_unit': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
            'serv_desc': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00'}),
            'serv_tota': forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01', 'value': '0.00', 'readonly': True}),
        }
        labels = {
            'serv_prod': 'Serviço',
            'serv_quan': 'Quantidade',
            'serv_unit': 'Preço Unitário',
            'serv_desc': 'Desconto',
        }

    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)

        super().__init__(*args, **kwargs)

        try:
            produtos_qs = Produtos.objects.using(database).all()
            if empresa_id:
                produtos_qs = produtos_qs.filter(prod_empr=str(empresa_id))
            self.servicos = produtos_qs.order_by('prod_nome')[:500]
        except Exception as e:
            print(f"Erro ao carregar itens: {e}")
            self.servicos = Produtos.objects.none()

    def clean(self):
        cleaned = super().clean()
        logging.getLogger(__name__).debug(
            "[ServicosOsForm.clean] serv_prod=%s serv_quan=%s serv_unit=%s serv_desc=%s",
            cleaned.get('serv_prod'), cleaned.get('serv_quan'), cleaned.get('serv_unit'), cleaned.get('serv_desc')
        )
        return cleaned
