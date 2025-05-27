from pyexpat import model
from django.db import models
from django.contrib.postgres.fields import ArrayField

class ImplantacaoTela(models.Model):
    MODULOS_CHOICES = [
        ('cadastro', 'Cadastros'),
        ('estoque', 'Estoque'),
        ('compras', 'Compras'),
        ('vendas', 'Vendas'),
        ('financeiro', 'Financeiro'),
        ('agricola', 'Agrícola'),
        ('os', 'Ordem de Serviço'),
        ('transportes', 'Transportes'),
        ('confeccao', 'Confecção'),
        ('materiais', 'Controle de Materiais'),
    ]

    TELAS_POR_MODULO = {
        'cadastro': ['Entidades', 'Centros de Custos', 'CFOPs', 'Grupo de Entidades', 'Mensagens Fiscais', 'Condições de Recebimento'],
        'estoque': ['Cadastro de Produtos', 'Entradas', 'Saídas', 'Saldo', 'Etiquetas'],
        'compras': ['Entrada Xml', 'Pedidos de Compra', 'Relatórios', 'Nota de Entrada Própria'],
        'vendas': ['Pedidos de Venda', 'Orçamentos', 'Nota Fiscal', 'Relatórios'],
        'financeiro': ['Contas a Pagar', 'Contas a Receber', 'Fluxo de Caixa'],
        'agricola': ['Talhões', 'Aplicações', 'Colheitas', 'Abastecimento'],
        'os': ['Abertura de OS', 'Execução', 'Encerramento', 'Relatórios'],
        'transportes': ['MDFe', 'Cte', 'Rotas', 'Entregas', 'Motoristas'],
        'confeccao': ['Confecção de Jóias', 'Ordens de Produção'],
        'materiais': ['Consumo', 'Requisição', 'Estoque Interno'],
    }
    Empresa = models.IntegerField(default=1)
    Filial = models.IntegerField(default=1)
    cliente = models.CharField(max_length=120)
    modulos = ArrayField(models.CharField(max_length=30), blank=True, default=list)
    telas = ArrayField(models.CharField(max_length=1000), blank=True, default=list)
    implantador = models.CharField(max_length=120)
    data_implantacao = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('nao_iniciado', 'Não Iniciado'),
            ('em_andamento', 'Em Andamento'),
            ('finalizado', 'Finalizado'),
        ],
        default='nao_iniciado'
    )
    treinado = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)
    criado_em =models.DateField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar módulos escolhidos
        for modulo in self.modulos:
            if modulo not in dict(self.MODULOS_CHOICES).keys():
                raise ValidationError(f"Módulo inválido: {modulo}")
        
        # Validar telas
        telas_validas = []
        for modulo in self.modulos:
            telas_validas += self.TELAS_POR_MODULO.get(modulo, [])
        
        for tela in self.telas:
            if tela not in telas_validas:
                raise ValidationError(f"A tela '{tela}' não pertence aos módulos selecionados.")
    
    class Meta:
        db_table = 'implantacoes'
        managed = False
       
        
