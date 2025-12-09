from django import forms
import logging
from django.forms import inlineformset_factory
from ..models import Servicososexterna, Osexterna
from Produtos.models import Produtos
from Entidades.models import Entidades


class ServicososexternaForm(forms.ModelForm):
    class Meta:
        model = Servicososexterna
        fields = '__all__'
        
        widgets = {
            'serv_prod': forms.HiddenInput(),
            'serv_desc': forms.Textarea(attrs={'rows': 4}),
            'serv_quan': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_valo_unit': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_valo_tota': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_temp_esti': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'serv_os': forms.HiddenInput(),
            'serv_empr': forms.HiddenInput(),
            'serv_fili': forms.HiddenInput(),
            'serv_sequ': forms.HiddenInput(),
            'serv_conc': forms.CheckboxInput(),
            'serv_temp_util': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'serv_km_said': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_km_cheg': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_km_reto': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_km_tota': forms.NumberInput(attrs={'step': '0.01'}),
            'serv_data_etap': forms.DateInput(attrs={'type': 'date'}),    
        
        }
        
        labels = {
            'serv_prod': 'Serviço',
            'serv_desc': 'Descrição',
            'serv_quan': 'Quantidade',
            'serv_valo_unit': 'Valor Unitário',
            'serv_valo_tota': 'Valor Total',
            'serv_temp_esti': 'Tempo Estimado',
            'serv_os': 'Ordem de Serviço',
            'serv_empr': 'Empresa',
            'serv_fili': 'Filial',
            'serv_sequ': 'Sequencial',
            'serv_conc': 'Concluído',
            'serv_temp_util': 'Tempo Utilizado',
            'serv_km_said': 'KM Saída',
            'serv_km_cheg': 'KM Chegada',
            'serv_km_reto': 'KM Retorno',
            'serv_km_tota': 'KM Total',
            'serv_data_etap': 'Data da Etapa',    
        }
    
    
    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)
        filial_id = kwargs.pop('filial_id', None)

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
            "[ServicososexternaForm.clean] serv_desc=%s serv_quan=%s serv_valo_unit=%s serv_valo_tota=%s",   
            cleaned.get('serv_desc'), cleaned.get('serv_quan'), cleaned.get('serv_valo_unit'), cleaned.get('serv_valo_tota')
        )
        return cleaned


    
        
class OsexternaForm(forms.ModelForm):
    class Meta:
        model = Osexterna
        fields = '__all__'
        
        widgets = {
            'osex_empr': forms.HiddenInput(),
            'osex_fili': forms.HiddenInput(),
            'osex_codi': forms.HiddenInput(),
            'osex_clie': forms.HiddenInput(),
            'osex_resp': forms.HiddenInput(),      
            'osex_valo_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'readonly': True}),
            'osex_data_aber': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'osex_data_fech': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'osex_canc_just': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'osex_canc_usua': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'step': '1'}),
            'osex_stat': forms.Select(attrs={'class': 'form-control'}),
            'osex_usua': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'step': '1'}),
            'osex_km_inic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'osex_km_tota': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            
        }
        
        labels = {
            'osex_clie': 'Cliente',
            'osex_resp': 'Responsável',
            'osex_valo_tota': 'Valor Total',
            'osex_data_aber': 'Data de Abertura',
            'osex_data_fech': 'Data de Fechamento',
            'osex_canc_just': 'Justificativa de Cancelamento',
            'osex_canc_usua': 'Usuário de Cancelamento',
            'osex_stat': 'Status',
            'osex_usua': 'Usuário',
            'osex_km_inic': 'KM Inicial',
            'osex_km_tota': 'KM Total',

        }
        
    def __init__(self, *args, **kwargs):
        database = kwargs.pop('database', 'default')
        empresa_id = kwargs.pop('empresa_id', None)
        filial_id = kwargs.pop('filial_id', None)

        super().__init__(*args, **kwargs)

        try:
            clientes = Entidades.objects.using(database).filter(
                enti_tipo_enti__icontains='CL'
            )
            if empresa_id:
                clientes = clientes.filter(enti_empr=str(empresa_id))

            self.fields['osex_clie'] = forms.ModelChoiceField(
                queryset=clientes.order_by('enti_nome'),
                empty_label="Selecione um cliente",
                widget=forms.HiddenInput()
            )
            self.fields['osex_clie'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
        except Exception as e:
            print(f"Erro ao carregar clientes: {e}")
            self.fields['osex_clie'] = forms.ModelChoiceField(queryset=Entidades.objects.none(), widget=forms.HiddenInput())

        try:
            responsavel = Entidades.objects.using(database).filter(
                enti_tipo_enti__in=['VE', 'FU']
            )
            if empresa_id:
                responsavel = responsavel.filter(enti_empr=str(empresa_id))

            self.fields['osex_resp'] = forms.ModelChoiceField(
                queryset=responsavel.order_by('enti_nome'),
                empty_label="Selecione o responsável",
                widget=forms.HiddenInput()
            )
            self.fields['osex_resp'].label_from_instance = lambda obj: f"{obj.enti_clie} - {obj.enti_nome}"
        except Exception as e:
            print(f"Erro ao carregar responsáveis: {e}")
            self.fields['osex_resp'] = forms.ModelChoiceField(queryset=Entidades.objects.none(), widget=forms.HiddenInput())

        
        self.fields['osex_stat'].choices = [
            (0, "Aberta"),
            (1, "Em assinatura"),
            (2, "Assinada"),
            (3, "Cancelada"),
            (4, "Finalizada"),
        ]
