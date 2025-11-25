from django import forms
from django.db import transaction
from .models import Centrodecustos


class CentrodecustosForm(forms.ModelForm):
    class Meta:
        model = Centrodecustos
        fields = [
            'cecu_empr', 'cecu_nome', 'cecu_niv1', 'cecu_anal'
        ]
        widgets = {
            'cecu_empr': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.empresa_id = kwargs.pop('empresa_id', None)
        super().__init__(*args, **kwargs)
        
        # Se tiver empresa_id, define no campo hidden
        if self.empresa_id and not self.instance.pk:
            self.fields['cecu_empr'].initial = self.empresa_id

    def clean_cecu_niv1(self):
        """Valida e converte o campo pai para inteiro"""
        pai = self.cleaned_data.get('cecu_niv1')
        if pai:
            try:
                pai = int(pai)
            except (ValueError, TypeError):
                raise forms.ValidationError('Código do pai inválido.')
        return pai

    def clean(self):
        cleaned = super().clean()
        anal = cleaned.get('cecu_anal')
        parent = cleaned.get('cecu_niv1')
        empresa = cleaned.get('cecu_empr') or self.empresa_id
        
        # Conta analítica sempre precisa de pai
        if anal == 'A' and not parent:
            raise forms.ValidationError('Conta analítica requer uma Conta Pai (Sintética).')
        
        # Valida se o pai existe e está na mesma empresa
        if parent and empresa:
            try:
                parent_obj = Centrodecustos.objects.get(
                    cecu_empr=empresa,
                    cecu_redu=parent
                )
                # Verifica se o pai pode ter filhos (não está no limite)
                if anal and parent_obj.cecu_anal == 'A':
                    # O model.save() vai converter o pai para sintético automaticamente
                    pass
            except Centrodecustos.DoesNotExist:
                raise forms.ValidationError(f'Conta pai {parent} não encontrada na empresa {empresa}.')
        
        return cleaned