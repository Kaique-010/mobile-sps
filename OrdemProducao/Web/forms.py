from django import forms

from ..models import Ordemproducao


class OrdemproducaoForm(forms.ModelForm):
    class Meta:
        model = Ordemproducao
        fields = [
            'orpr_nuca',
            'orpr_tipo',
            'orpr_clie',
            'orpr_entr',
            'orpr_prev',
            'orpr_vend',
            'orpr_gara',
            'orpr_cort',
            'orpr_valo',
            'orpr_desc',
            'orpr_prod',
            'orpr_quan',
            'orpr_gram_clie',
            'orpr_stat',
        ]
        widgets = {
            'orpr_entr': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'orpr_prev': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'orpr_desc': forms.Textarea(attrs={'rows': 3}),
        }
