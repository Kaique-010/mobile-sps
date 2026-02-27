from django import forms
from django.db import transaction
from django.db.models import Max
from .models import Entidades
import logging

logger = logging.getLogger(__name__)


class EntidadesForm(forms.ModelForm):
    enti_situ = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input', 
            'role': 'switch', 
            'style': 'width: 3em; height: 1.5em;'
        }),
        required=False,
        label='Situação'
    )
    
    is_transportadora = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input', 
            'role': 'switch', 
            'style': 'width: 3em; height: 1.5em;'
        }),
        required=False,
        label='É Transportadora?'
    )

    class Meta:
        model = Entidades
        fields = [
            'enti_nome', 'enti_tipo_enti', 'enti_fant', 
            'enti_cpf', 'enti_cnpj', 'enti_insc_esta', 'enti_cep', 'enti_ende', 
            'enti_nume', 'enti_cida','enti_codi_cida', 'enti_esta', 'enti_fone', 'enti_celu', 
            'enti_emai', 'enti_situ'
        ]
        widgets = {
            'enti_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'enti_tipo_enti': forms.Select(attrs={'class': 'form-control'}),
            'enti_fant': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia'}),
            'enti_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CPF', 'maxlength': '11'}),
            'enti_cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNPJ', 'maxlength': '14'}),
            'enti_insc_esta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inscrição Estadual'}),
            'enti_cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CEP', 'maxlength': '8'}),
            'enti_ende': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Endereço'}),
            'enti_nume': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'enti_cida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade'}),
            'enti_codi_cida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código IBGE'}),
            'enti_esta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estado', 'maxlength': '2'}),
            'enti_fone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone', 'maxlength': '14'}),
            'enti_celu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Celular', 'maxlength': '15'}),
            'enti_emai': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Pessoal'}),
        }

    def clean_enti_situ(self):
        return '1' if self.cleaned_data.get('enti_situ') else '0'

    def __init__(self, *args, db_name=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_name = db_name  # Guarda o nome do banco para ser usado no save()
        self.request = request  # Store the request object

        # Ajusta o valor inicial do campo booleano com base no valor '0'/'1' do model
        if self.instance and self.instance.pk:
            self.fields['enti_situ'].initial = (self.instance.enti_situ == '1')
            self.fields['is_transportadora'].initial = (self.instance.enti_tien == 'T')

        # Tornar certos campos não obrigatórios
        for field in ['enti_cpf', 'enti_cnpj', 'enti_fone', 'enti_emai',
                      'enti_insc_esta', 'enti_fant', 'enti_ende', 
                      'enti_cida', 'enti_esta', 'enti_clie']:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        cpf = cleaned_data.get('enti_cpf')
        cnpj = cleaned_data.get('enti_cnpj')
        ie = cleaned_data.get('enti_insc_esta')
        cep = cleaned_data.get('enti_cep')
        
        from .utils import buscar_endereco_por_cep
        
        if cep:
            endereco = buscar_endereco_por_cep(cep)
            if endereco:
                cleaned_data.update(endereco)
                cleaned_data['enti_codi_cida'] = endereco.get('codi_cidade')
            else:
                self.add_error('enti_cep', "CEP inválido ou não encontrado.")

        # Validação para não permitir CPF junto com CNPJ ou Inscrição Estadual
        if cpf and (cnpj or ie):
            raise forms.ValidationError("Se o CPF for fornecido, CNPJ e Inscrição Estadual não devem ser preenchidos.")
        
        return cleaned_data

    def save(self, commit=True):
        logger.debug("Método save() chamado.")  # Log de depuração
        if not hasattr(self, 'request') or not self.request:
            raise ValueError("Erro: requisição não definida no formulário. Verifique se o request foi passado corretamente.")

        db_alias = self.request.db_alias
        if not db_alias:
            raise ValueError("Erro: banco de dados não definido no formulário. Verifique se a sessão contém 'banco'.")

        instance = super().save(commit=False)

        if self.cleaned_data.get('is_transportadora'):
            instance.enti_tien = 'T'
            instance.enti_tipo_enti = 'FO'  # Força tipo Fornecedor se for transportadora
        elif instance.enti_tien == 'T':
            # Se era transportadora e desmarcou, volta para Entidade padrão
            instance.enti_tien = 'E'
            
        # Atribui empresa/filial a partir dos headers (com fallback à sessão)
        try:
            headers = getattr(self.request, 'headers', {})
        except Exception:
            headers = {}
        empresa_header = headers.get('X-Empresa') or self.request.META.get('HTTP_X_EMPRESA')
        filial_header = headers.get('X-Filial') or self.request.META.get('HTTP_X_FILIAL')
        empresa_sess = self.request.session.get('empresa_id')
        filial_sess = self.request.session.get('filial_id')

        empresa_val = empresa_header or empresa_sess
        filial_val = filial_header or filial_sess  # reservado para futuros usos

        if instance.enti_empr is None:
            if empresa_val is None:
                raise ValueError("A empresa (`enti_empr`) deve ser informada via cabeçalho X-Empresa ou sessão antes de salvar.")
            try:
                instance.enti_empr = int(empresa_val)
            except (ValueError, TypeError):
                raise ValueError("Header X-Empresa inválido: não é numérico.")

        with transaction.atomic(using=db_alias):
            # Verifica se é uma criação (instance.pk é None) ou uma edição (instance.pk não é None)
            if not instance.enti_clie:
                # Somente para criação: calcula o próximo enti_clie
                logger.debug(f"Banco de dados sendo usado: {db_alias}")
                logger.debug(f"Consulta SQL: SELECT MAX(enti_clie) FROM Entidades;")

                # Obtém o maior valor de `enti_clie` no banco de dados
                ultimo_codigo = Entidades.objects.using(db_alias).aggregate(Max("enti_clie"))["enti_clie__max"]
                
                # Log para depuração
                logger.debug(f"Último código encontrado: {ultimo_codigo}")

                # Se não houver registros, define como 1, caso contrário, incrementa o último código
                if ultimo_codigo is None:
                    instance.enti_clie = 1
                else:
                    instance.enti_clie = ultimo_codigo + 1

                # Log para depuração
                logger.debug(f"Novo código definido: {instance.enti_clie}")
            else:
                # Para edição, mantém o enti_clie existente
                logger.debug(f"Editando registro existente. enti_clie mantido: {instance.enti_clie}")

            if commit:
                instance.save(using=db_alias)
                logger.debug(f"Registro salvo com sucesso: {instance.enti_clie}")

        return instance