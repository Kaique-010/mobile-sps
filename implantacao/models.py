from pyexpat import model
from django.db import models

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
    modulo = models.CharField(max_length=30, choices=MODULOS_CHOICES)
    tela = models.CharField(max_length=100)  
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
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Valida se a tela realmente pertence ao módulo informado
        telas_validas = self.TELAS_POR_MODULO.get(self.modulo, [])
        if self.tela not in telas_validas:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"A tela '{self.tela}' não pertence ao módulo '{self.modulo}'.")

    def __str__(self):
        return f"{self.cliente} - {self.modulo} > {self.tela}"
