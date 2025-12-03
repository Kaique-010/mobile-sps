# central/forms.py
from django import forms
from .models import CentralDeAjuda

class CentralDeAjudaForm(forms.ModelForm):
    class Meta:
        model = CentralDeAjuda
        fields = [
            "cent_modu",
            "cent_titu",
            "cent_cont",
            "cent_video",
        ]
        widgets = {
            "cent_modu": forms.Select(attrs={"class": "form-select"}),
            "cent_titu": forms.TextInput(attrs={"class": "form-control", "placeholder": "Título"}),
            "cent_cont": forms.Textarea(attrs={"rows": 5, "placeholder": "Conteúdo"}),
            "cent_video": forms.TextInput(attrs={"class": "form-control", "placeholder": "Link do Vídeo"}),
        }
        
        labels = {
            "cent_modu": "Módulo",
            "cent_titu": "Título",
            "cent_cont": "Conteúdo",
            "cent_video": "Link do Vídeo",
        }
