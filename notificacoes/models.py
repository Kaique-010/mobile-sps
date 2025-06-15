# models/notificacoes.py
from django.db import models
from Licencas.models import Usuarios

class Notificacao(models.Model):
    usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=100)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=50)  
    data_criacao = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    class Meta:
        ordering = ['-data_criacao']
        db_table = 'notificacoes'
