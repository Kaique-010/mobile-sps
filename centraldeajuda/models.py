# central/models.py
from django.db import models
from Licencas.models import Usuarios

class CentralDeAjuda(models.Model):
    MODULOS = [
        ('1', 'Cadastros'),
        ('2', 'Estoque'),
        ('3', 'Vendas e Saídas'),
        ('4', 'Compras e Entradas'),
        ('5', 'Financeiro'),
        ('6', 'Caixa Diário'),
        ('7', 'Outros'),
    ]

    cent_empr = models.IntegerField()  # slug/empresa
    cent_modu = models.CharField(max_length=2, choices=MODULOS)
    cent_titu = models.CharField(max_length=255)
    cent_cont = models.TextField()  # conteúdo html ou markdown
    cent_data_cria = models.DateTimeField(auto_now_add=True)
    cent_data_atual = models.DateTimeField(auto_now=True)
    cent_usua_crio = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    cent_video = models.CharField(max_length=255, null=True, blank=True) 

    class Meta:
        ordering = ['-cent_data_cria']

    def __str__(self):
        return self.cent_titu



class CentralProgresso(models.Model):
    usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    ajuda = models.ForeignKey(CentralDeAjuda, on_delete=models.CASCADE)
    progresso = models.IntegerField(default=0)  # porcentagem
    atualizado = models.DateTimeField(auto_now=True)