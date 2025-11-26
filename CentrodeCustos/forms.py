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
        self.fields['cecu_nome'].required = True

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")

        # checar se está tentando criar filho em analítico
        if parent:
            qs = Centrodecustos.objects
            if self.db_alias:
                qs = qs.using(self.db_alias)

            # identificar pai por expandido quando possível (mesmo sem ponto), senão por reduzido
            pai = None
            if isinstance(parent, str):
                pai = qs.filter(cecu_empr=self.empresa_id, cecu_expa=parent).first()
            if not pai:
                try:
                    parent_redu = int(str(parent))
                    pai = qs.filter(cecu_empr=self.empresa_id, cecu_redu=parent_redu).first()
                except Exception:
                    pai = None
            if not pai:
                raise forms.ValidationError("Centro pai não encontrado.")
            parent_expa = pai.cecu_expa
            parent_redu = int(str(pai.cecu_redu))

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

        # Em edição, não alterar códigos/níveis/vínculos; apenas atualizar campos editáveis
        if getattr(obj, 'cecu_redu', None):
            if commit:
                if self.db_alias:
                    obj.save(using=self.db_alias)
                else:
                    obj.save()
            return obj

        if parent:
            qs = Centrodecustos.objects
            if self.db_alias:
                qs = qs.using(self.db_alias)

            # identificar pai por expandido quando possível (mesmo sem ponto), senão por reduzido
            pai = None
            if isinstance(parent, str):
                pai = qs.filter(cecu_empr=empresa, cecu_expa=parent).first()
            if not pai:
                try:
                    parent_redu = int(str(parent))
                    pai = qs.filter(cecu_empr=empresa, cecu_redu=parent_redu).first()
                except Exception:
                    pai = None
            if not pai:
                raise forms.ValidationError("Centro pai não encontrado.")
            parent_expa = pai.cecu_expa
            parent_redu = int(str(pai.cecu_redu))

            partes = parent_expa.split(".")
            nivel_parent = len(partes)

            # Normalizar referência e coletar existentes por prefixo + nível,
            # para respeitar dados legados independentemente do `cecu_niv1` gravado
            if nivel_parent >= 2:
                pai_segundo_expa = f"{partes[0]}.{partes[1]}"
                pai_segundo_redu = int(pai_segundo_expa.replace(".", ""))
            else:
                pai_segundo_expa = None
                pai_segundo_redu = parent_redu

            if nivel_parent == 1:
                prefixo = f"{partes[0]}."
                filhos_expas = list(
                    qs.filter(cecu_empr=empresa, cecu_expa__startswith=prefixo, cecu_nive=2)
                    .order_by("cecu_redu")
                    .values_list("cecu_expa", flat=True)
                )
            else:
                prefixo = f"{partes[0]}.{partes[1]}."
                filhos_expas = list(
                    qs.filter(cecu_empr=empresa, cecu_expa__startswith=prefixo, cecu_nive=3)
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
                for expa in filhos_expas:
                    p = expa.split(".")
                    if len(p) >= 3 and p[0] == partes[0] and p[1] == partes[1]:
                        try:
                            usados.append(int(p[2]))
                        except Exception:
                            pass
                proximo_terceiro = (max(usados) + 1) if usados else 1
                sufixo3 = str(proximo_terceiro).zfill(DIGITOS[2])
                codigo = f"{partes[0]}.{partes[1]}.{sufixo3}"
                tipo = MASCARA[2]
                obj.cecu_nive = 3

            obj.cecu_expa = codigo
            obj.cecu_anal = tipo
            from django.db.models import Max
            max_redu = qs.filter(cecu_empr=empresa).aggregate(m=Max("cecu_redu")).get("m")
            obj.cecu_redu = (int(max_redu) + 1) if max_redu else 1
            # Sempre referenciar o pai de primeiro nível em cecu_niv1 (valores 1,2,3,4)
            try:
                obj.cecu_niv1 = int(partes[0])
            except Exception:
                obj.cecu_niv1 = parent_redu
        else:
            try:
                codigo, tipo = gerar_proximo_codigo(None, empresa, self.db_alias)
            except Exception as e:
                raise forms.ValidationError(str(e))
            obj.cecu_expa = codigo
            obj.cecu_anal = tipo
            obj.cecu_nive = len(codigo.split("."))
            from django.db.models import Max
            qs_all = Centrodecustos.objects.using(self.db_alias) if self.db_alias else Centrodecustos.objects
            max_redu = qs_all.filter(cecu_empr=empresa).aggregate(m=Max("cecu_redu")).get("m")
            obj.cecu_redu = (int(max_redu) + 1) if max_redu else 1

        if commit:
            if self.db_alias:
                obj.save(using=self.db_alias)
            else:
                obj.save()

        return obj
