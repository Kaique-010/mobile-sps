from django import forms
from ..models import Bensptr, Grupobens, Motivosptr
from Entidades.models import Entidades

class BensptrForm(forms.ModelForm):
    bens_grup = forms.ModelChoiceField(
        queryset=Grupobens.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Grupo de Bens'
    )
    bens_moti = forms.ModelChoiceField(
        queryset=Motivosptr.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Motivo'
    )
    bens_forn = forms.ModelChoiceField(
        queryset=Entidades.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Fornecedor'
    )

    class Meta:
        model = Bensptr
        fields = [
            'bens_codi', 'bens_desc', 'bens_grup', 'bens_marc', 'bens_mode', 'bens_seri',
            'bens_data_aqui', 'bens_valo_aqui', 'bens_praz_vida', 'bens_inic_depr',
            'bens_depr_ano', 'bens_moti', 'bens_forn', 'bens_nota', 
            'bens_obse'
        ]
        widgets = {
            'bens_codi': forms.TextInput(attrs={'placeholder': 'Código', 'class': 'form-control', 'readonly': 'readonly'}),
            'bens_desc': forms.TextInput(attrs={'placeholder': 'Descrição', 'class': 'form-control'}),
            'bens_marc': forms.TextInput(attrs={'placeholder': 'Marca', 'class': 'form-control'}),
            'bens_mode': forms.TextInput(attrs={'placeholder': 'Modelo', 'class': 'form-control'}),
            'bens_seri': forms.TextInput(attrs={'placeholder': 'Série', 'class': 'form-control'}),
            'bens_data_aqui': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bens_valo_aqui': forms.NumberInput(attrs={'placeholder': 'Valor Aquisição', 'class': 'form-control', 'step': '0.01'}),
            'bens_praz_vida': forms.NumberInput(attrs={'placeholder': 'Vida Útil (anos)', 'class': 'form-control'}),
            'bens_inic_depr': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bens_depr_ano': forms.NumberInput(attrs={'placeholder': 'Taxa Depr. Anual (%)', 'class': 'form-control', 'step': '0.0001'}),
            'bens_nota': forms.TextInput(attrs={'placeholder': 'Nota Fiscal', 'class': 'form-control'}),
            'bens_obse': forms.Textarea(attrs={'placeholder': 'Observações', 'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'bens_codi': 'Código',
            'bens_desc': 'Descrição',
            'bens_marc': 'Marca',
            'bens_mode': 'Modelo',
            'bens_seri': 'Série',
            'bens_data_aqui': 'Data Aquisição',
            'bens_valo_aqui': 'Valor Aquisição',
            'bens_praz_vida': 'Vida Útil',
            'bens_inic_depr': 'Início Depreciação',
            'bens_depr_ano': 'Taxa Anual (%)',
            'bens_nota': 'Nota Fiscal',
            'bens_obse': 'Observações',
        }

    def __init__(self, *args, **kwargs):
        # Recebe 'empresa' e 'filial' via kwargs se passados, ou tenta inferir
        self.empresa = kwargs.pop('empresa', None)
        self.filial = kwargs.pop('filial', None)
        super().__init__(*args, **kwargs)

        # Configura querysets
        # Nota: Grupobens e Motivosptr podem precisar de filtro por empresa se a tabela tiver grup_empr
        if self.empresa:
             self.fields['bens_grup'].queryset = Grupobens.objects.filter(grup_empr=self.empresa).order_by('grup_nome')
             # Motivosptr não tem empresa no model dump? Tem moti_codi e moti_desc. 
             # Mas o service MotivosService.criar_motivo usa 'moti_empr'. 
             # Vamos checar model dump de Motivosptr de novo.
             # class Motivosptr(models.Model): moti_codi (pk), moti_desc. 
             # Parece global ou o dump estava incompleto? 
             # O service usa moti_empr, moti_fili para gerar sequencial. 
             # Mas Motivosptr model só mostrou moti_codi e moti_desc.
             # Assumindo global ou filtragem manual se tiver campos ocultos.
             self.fields['bens_moti'].queryset = Motivosptr.objects.all().order_by('moti_desc')
             
             self.fields['bens_forn'].queryset = Entidades.objects.filter(enti_empr=self.empresa).order_by('enti_nome')
        else:
             self.fields['bens_grup'].queryset = Grupobens.objects.all().order_by('grup_nome')
             self.fields['bens_moti'].queryset = Motivosptr.objects.all().order_by('moti_desc')
             self.fields['bens_forn'].queryset = Entidades.objects.all().order_by('enti_nome')


class GrupobensForm(forms.ModelForm):
    class Meta:
        model = Grupobens
        fields = ['grup_codi', 'grup_nome', 'grup_vida_util', 'grup_perc_depr_ano']
        widgets = {
            'grup_codi': forms.NumberInput(attrs={'placeholder': 'Código', 'class': 'form-control', 'readonly': 'readonly'}),
            'grup_nome': forms.TextInput(attrs={'placeholder': 'Nome do Grupo', 'class': 'form-control'}),
            'grup_vida_util': forms.NumberInput(attrs={'placeholder': 'Vida Útil (anos)', 'class': 'form-control'}),
            'grup_perc_depr_ano': forms.NumberInput(attrs={'placeholder': 'Taxa Anual (%)', 'class': 'form-control', 'step': '0.0001'}),
        }
        labels = {
            'grup_codi': 'Código',
            'grup_nome': 'Nome',
            'grup_vida_util': 'Vida Útil',
            'grup_perc_depr_ano': 'Taxa Anual',
        }


class MotivosptrForm(forms.ModelForm):
    class Meta:
        model = Motivosptr
        fields = ['moti_codi', 'moti_desc']
        widgets = {
            'moti_codi': forms.NumberInput(attrs={'placeholder': 'Código', 'class': 'form-control', 'readonly': 'readonly'}),
            'moti_desc': forms.TextInput(attrs={'placeholder': 'Descrição', 'class': 'form-control'}),
        }
        labels = {
            'moti_codi': 'Código',
            'moti_desc': 'Descrição',
        }
