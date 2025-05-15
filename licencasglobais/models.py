from django.db import models

class LicencaGlobal(models.Model):
    id = models.AutoField(primary_key=True)
    lice_nome = models.CharField(max_length=255)
    lice_docu = models.CharField(max_length=20) 
    lice_slug = models.CharField(max_length=255, unique=True)
    lice_stat = models.BooleanField(default=True)

    # Módulos liberados
    modulo_dashboard = models.BooleanField(default=False)
    modulo_entidades = models.BooleanField(default=False)
    modulo_usuarios = models.BooleanField(default=False)
    modulo_licencas = models.BooleanField(default=False)
    modulo_listacasamento = models.BooleanField(default=False)
    modulo_orcamentos = models.BooleanField(default=False)
    modulo_pedidos = models.BooleanField(default=False)
    modulo_entradas_estoque = models.BooleanField(default=False)
    modulo_saida_estoque = models.BooleanField(default=False)
    modulo_produtos = models.BooleanField(default=False)

    # Timestamps
    lice_data_cria = models.DateTimeField(auto_now_add=True)
    lice_data_atlz = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.lice_nome

    class Meta:
        db_table = 'licencasglobal'
        verbose_name = 'Licença Global'
        verbose_name_plural = 'Licenças Globais'
        ordering = ['lice_nome']