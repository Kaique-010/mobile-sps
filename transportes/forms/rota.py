from django import forms
from transportes.models import Cte
from Entidades.models import Entidades
from core.utils import get_licenca_db_config

class CteRotaForm(forms.ModelForm):
    class Meta:
        model = Cte
        fields = [
            'cidade_coleta', 'cidade_entrega', 'pedagio', 'peso_total',
            'tarifa', 'frete_peso', 'frete_valor', 'total_valor', 'outras_observacoes'
        ]
        widgets = {
            'cidade_coleta': forms.NumberInput(attrs={'class': 'form-control'}),
            'cidade_entrega': forms.NumberInput(attrs={'class': 'form-control'}),
            'pedagio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'tarifa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frete_peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'frete_valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'outras_observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            db_alias = 'default'
            if self.request:
                 db_alias = get_licenca_db_config(self.request)
            
            # Preenchimento automático de Coleta
            if not self.instance.cidade_coleta and self.instance.remetente:
                remetente = Entidades.objects.using(db_alias).filter(pk=self.instance.remetente).first()
                if remetente and remetente.enti_codi_cida:
                    try:
                        self.fields['cidade_coleta'].initial = int(remetente.enti_codi_cida)
                    except ValueError:
                        pass
            
            # Preenchimento automático de Entrega
            if not self.instance.cidade_entrega and self.instance.destinatario:
                destinatario = Entidades.objects.using(db_alias).filter(pk=self.instance.destinatario).first()
                if destinatario and destinatario.enti_codi_cida:
                    try:
                        self.fields['cidade_entrega'].initial = int(destinatario.enti_codi_cida)
                    except ValueError:
                        pass
