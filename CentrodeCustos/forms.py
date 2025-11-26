# forms.py
from django import forms
from .models import Centrodecustos
from .service import gerar_proximo_codigo, MASCARA, DIGITOS


class CentrodecustosForm(forms.ModelForm):
    parent = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Centrodecustos
        fields = ['cecu_empr', 'cecu_nome', 'parent']
        widgets = {
            'cecu_empr': forms.HiddenInput(),
            'cecu_nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa_id = kwargs.pop("empresa_id")
        self.db_alias = kwargs.pop("db_alias", None)
        super().__init__(*args, **kwargs)
        self.fields['cecu_empr'].initial = self.empresa_id

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")

        # checar se está tentando criar filho em analítico
        if parent:
            from .models import Centrodecustos
            qs = Centrodecustos.objects
            if self.db_alias:
                qs = qs.using(self.db_alias)

            # aceitar parent como expa (com pontos) ou redu (inteiro)
            if isinstance(parent, str) and "." in parent:
                parent_expa = parent
                parent_redu = int(parent.replace(".", ""))
            else:
                parent_redu = int(parent)
                pai = qs.filter(cecu_expa__isnull=False, cecu_empr=self.empresa_id, cecu_redu=parent_redu).first()
                if not pai:
                    raise forms.ValidationError("Centro pai não encontrado.")
                parent_expa = pai.cecu_expa

            # validação por máscara (independe do dado gravado)
            nivel_parent = len(str(parent_expa).split("."))
            if nivel_parent >= len(MASCARA):
                # nível máximo → só permite filhos se negócio for mesmo nível (grupos no nível 3)
                # aqui não bloqueamos; a lógica de save cuida do nível.
                pass
            else:
                tipo_parent_esperado = MASCARA[nivel_parent - 1]
                if tipo_parent_esperado == "A":
                    raise forms.ValidationError("Centros analíticos não podem ter filhos.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)

        parent = self.cleaned_data.get("parent", None)
        empresa = int(self.cleaned_data["cecu_empr"] or 0)

        if parent:
            from .models import Centrodecustos
            qs = Centrodecustos.objects
            if self.db_alias:
                qs = qs.using(self.db_alias)

            # aceitar parent em expa ou redu
            if isinstance(parent, str) and "." in parent:
                parent_expa = parent
                parent_redu = int(parent.replace(".", ""))
            else:
                parent_redu = int(parent)
                pai = qs.filter(cecu_empr=empresa, cecu_redu=parent_redu).first()
                if not pai:
                    raise forms.ValidationError("Centro pai não encontrado.")
                parent_expa = pai.cecu_expa

            partes = parent_expa.split(".")
            nivel_parent = len(partes)

            # filhos por vínculo cecu_niv1
            filhos_expas = list(
                qs.filter(cecu_empr=empresa, cecu_niv1=parent_redu)
                .order_by("cecu_redu")
                .values_list("cecu_expa", flat=True)
            )

            if nivel_parent == 1:
                usados = []
                for expa in filhos_expas:
                    p = expa.split(".")
                    if len(p) >= 2 and p[0] == partes[0]:
                        usados.append(int(p[1]))
                proximo_segundo = (max(usados) + 1) if usados else 1
                sufixo2 = str(proximo_segundo).zfill(DIGITOS[1])
                codigo = f"{partes[0]}.{sufixo2}"
                tipo = MASCARA[1]
                obj.cecu_nive = 2
            else:
                usados = []
                base_terceiro = int(partes[2]) if len(partes) >= 3 else 0
                for expa in filhos_expas:
                    p = expa.split(".")
                    if len(p) >= 3 and p[0] == partes[0] and p[1] == partes[1]:
                        usados.append(int(p[2]))
                proximo_terceiro = (max(usados) + 1) if usados else (base_terceiro + 1)
                sufixo3 = str(proximo_terceiro).zfill(DIGITOS[2])
                codigo = f"{partes[0]}.{partes[1]}.{sufixo3}"
                tipo = MASCARA[2]
                obj.cecu_nive = 3

            obj.cecu_expa = codigo
            obj.cecu_anal = tipo
            obj.cecu_redu = int(codigo.replace(".", ""))
            obj.cecu_niv1 = parent_redu
        else:
            # gerar raiz pelo serviço padrão
            try:
                codigo, tipo = gerar_proximo_codigo(None, empresa)
            except Exception as e:
                raise forms.ValidationError(str(e))
            obj.cecu_expa = codigo
            obj.cecu_anal = tipo
            obj.cecu_nive = len(codigo.split("."))
            obj.cecu_redu = int(codigo.replace(".", ""))

        if commit:
            if self.db_alias:
                obj.save(using=self.db_alias)
            else:
                obj.save()

        return obj
