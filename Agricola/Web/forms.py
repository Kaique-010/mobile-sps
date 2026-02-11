from django import forms
from ..models import (
    Fazenda, Talhao, CategoriaProduto, ProdutoAgro, 
    EstoqueFazenda, MovimentacaoEstoque, HistoricoMovimentacao,
    AplicacaoInsumos, Animal, EventoAnimal
)

# ====== Fazenda ======
class FazendaForm(forms.ModelForm):
    class Meta:
        model = Fazenda
        fields = ['faze_nome', 'faze_loca', 'faze_area_tota']
        widgets = {
            'faze_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Fazenda'}),
            'faze_loca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localização'}),
            'faze_area_tota': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
        labels = {
            'faze_nome': 'Nome da Fazenda',
            'faze_loca': 'Localização',
            'faze_area_tota': 'Área Total',
        }

# ====== Talhão ======
class TalhaoForm(forms.ModelForm):
    class Meta:
        model = Talhao
        fields = ['talh_faze', 'talh_nome', 'talh_area', 'talh_unmd']
        widgets = {
            'talh_faze': forms.HiddenInput(),
            'talh_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Talhão'}),
            'talh_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'talh_unmd': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unidade de Medida'}),
        }
        labels = {
            'talh_faze': 'Fazenda',
            'talh_nome': 'Nome do Talhão',
            'talh_area': 'Área',
            'talh_unmd': 'Unidade de Medida',
            
        }

# ====== Categoria Produto ======
class CategoriaProdutoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProduto
        fields = ['cate_nome']
        widgets = {
            'cate_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Categoria'}),
        }
        labels = {
            'cate_nome': 'Nome da Categoria',
        }

# ====== Produto Agro ======
class ProdutoAgroForm(forms.ModelForm):
    class Meta:
        model = ProdutoAgro
        fields = ['prod_codi_agro', 'prod_nome_agro', 'prod_cate_agro', 'prod_unmd_agro', 'prod_desc_agro', 'prod_cust_unit']
        widgets = {
            'prod_codi_agro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código'}),
            'prod_nome_agro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Produto'}),
            'prod_cate_agro': forms.Select(attrs={'class': 'form-select'}),
            'prod_unmd_agro': forms.Select(attrs={'class': 'form-select'}),
            'prod_desc_agro': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição'}),
            'prod_cust_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'prod_codi_agro': 'Código',
            'prod_nome_agro': 'Nome do Produto',
            'prod_cate_agro': 'Categoria',
            'prod_unmd_agro': 'Unidade de Medida',
            'prod_desc_agro': 'Descrição',
            'prod_cust_unit': 'Custo Unitário',
        }

# ====== Estoque Fazenda ======
class EstoqueFazendaForm(forms.ModelForm):
    class Meta:
        model = EstoqueFazenda
        fields = ['estq_faze', 'estq_prod', 'estq_quant', 'estq_cust_medi']
        widgets = {
            'estq_faze': forms.HiddenInput(),
            'estq_prod': forms.Select(attrs={'class': 'form-select'}),
            'estq_quant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'estq_cust_medi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }
        labels = {
            'estq_faze': 'Fazenda',
            'estq_prod': 'Produto',
            'estq_quant': 'Quantidade',
            'estq_cust_medi': 'Custo Médio',
        }

# ====== Movimentação Estoque ======
class MovimentacaoEstoqueForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'movi_estq_faze', 'movi_estq_prod', 'movi_estq_quant', 'movi_estq_tipo', 
            'movi_estq_moti', 'movi_estq_docu_refe', 'movi_estq_cust_unit', 'movi_estq_cust_tota'
        ]
        widgets = {
            'movi_estq_faze': forms.HiddenInput(),
            'movi_estq_prod': forms.HiddenInput(),
            'movi_estq_quant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'movi_estq_tipo': forms.Select(attrs={'class': 'form-select'}),
            'movi_estq_moti': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Motivo'}),
            'movi_estq_docu_refe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Documento Referência'}),
            'movi_estq_cust_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'movi_estq_cust_tota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
        }
        labels = {
            'movi_estq_faze': 'Fazenda',
            'movi_estq_prod': 'Produto',
            'movi_estq_quant': 'Quantidade',
            'movi_estq_tipo': 'Tipo',
            'movi_estq_moti': 'Motivo',
            'movi_estq_docu_refe': 'Documento Referência',
            'movi_estq_cust_unit': 'Custo Unitário',
            'movi_estq_cust_tota': 'Custo Total',
        }

# ====== Histórico Movimentação ======
class HistoricoMovimentacaoForm(forms.ModelForm):
    class Meta:
        model = HistoricoMovimentacao
        fields = '__all__'
        # Geralmente histórico é apenas visualização, mas deixo o form básico se necessário

# ====== Aplicação Insumos ======
class AplicacaoInsumosForm(forms.ModelForm):
    class Meta:
        model = AplicacaoInsumos
        fields = ['apli_talh', 'apli_prod', 'apli_quant', 'apli_obse']
        widgets = {
            'apli_talh': forms.HiddenInput(),
            'apli_prod': forms.HiddenInput(),
            'apli_quant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'apli_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'apli_talh': 'Talhão',
            'apli_prod': 'Produto Aplicado',
            'apli_quant': 'Quantidade',
            'apli_obse': 'Observação',
        }

# ====== Animal ======
class AnimalForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ['anim_faze', 'anim_ident', 'anim_raca', 'anim_data_nasc', 'anim_sexo', 'anim_peso_atual', 'anim_obse']
        widgets = {
            'anim_faze': forms.HiddenInput(),
            'anim_ident': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Identificação/Tag'}),
            'anim_raca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Raça'}),
            'anim_data_nasc': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'anim_sexo': forms.Select(attrs={'class': 'form-select'}),
            'anim_peso_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'anim_obse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'anim_faze': 'Fazenda',
            'anim_ident': 'Identificação/Tag',
            'anim_raca': 'Raça',
            'anim_data_nasc': 'Data de Nascimento',
            'anim_sexo': 'Sexo',
            'anim_peso_atual': 'Peso Atual',
            'anim_obse': 'Observação',
        }

# ====== Evento Animal ======
class EventoAnimalForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.db_alias = kwargs.pop('db_alias', 'default')
        super().__init__(*args, **kwargs)
        if self.db_alias != 'default':
            self.fields['evnt_anim'].queryset = Animal.objects.using(self.db_alias).all()

    class Meta:
        model = EventoAnimal
        fields = ['evnt_anim', 'evnt_tipo_even', 'evnt_data_even', 'evnt_cust', 'evnt_desc']
        widgets = {
            'evnt_anim': forms.HiddenInput(),
            'evnt_tipo_even': forms.Select(attrs={'class': 'form-select'}),
            'evnt_data_even': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'evnt_cust': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'evnt_desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'evnt_anim': 'Animal',
            'evnt_tipo_even': 'Tipo de Evento',
            'evnt_data_even': 'Data do Evento',
            'evnt_cust': 'Custo',
            'evnt_desc': 'Descrição',
        }
