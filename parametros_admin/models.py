from django.db import models

class Modulo(models.Model):
    modu_codi = models.AutoField(primary_key=True)
    modu_nome = models.CharField(max_length=50, unique=True, help_text="Nome do módulo")
    modu_desc = models.TextField(help_text="Descrição do módulo")
    modu_ativ = models.BooleanField(default=True, help_text="Módulo ativo no sistema")
    modu_icon= models.CharField(max_length=50, blank=True, help_text="Ícone do módulo")
    modu_orde = models.IntegerField(default=0, help_text="Ordem de exibição")

    class Meta:
        db_table = 'modulosmobile'        
        ordering = ['modu_orde', 'modu_nome']


class PermissaoModulo(models.Model):
    perm_codi = models.AutoField(primary_key=True)
    perm_empr = models.IntegerField(help_text="Código da empresa")
    perm_fili = models.IntegerField(help_text="Código da filial")
    perm_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='permissoes', db_column='perm_modu')
    perm_ativ = models.BooleanField(default=True, help_text="Módulo liberado")
    perm_usua_libe = models.IntegerField(blank=True, help_text="Usuário que liberou")
    perm_data_alte = models.DateTimeField(auto_now=True, help_text="Data de alteração")
    

    class Meta:
        db_table = 'permissoesmodulosmobile'
        unique_together = ('perm_empr', 'perm_fili', 'perm_modu')
        ordering = ['perm_empr', 'perm_fili', 'perm_modu']



class ParametroSistema(models.Model):
    para_codi = models.AutoField(primary_key=True)
    para_empr = models.IntegerField(help_text="Código da empresa")
    para_fili = models.IntegerField(help_text="Código da filial")
    para_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='parametros', db_column='para_modu_id')
    para_nome = models.CharField(max_length=50, help_text="Nome do parâmetro")
    para_desc = models.TextField(help_text="Descrição do parâmetro")
    para_valo = models.BooleanField(default=False, help_text="Valor do parâmetro")
    para_ativ = models.BooleanField(default=True, help_text="Parâmetro ativo")
    para_data_alte = models.DateTimeField(auto_now=True, help_text="Data de alteração")
    para_usua_alte = models.IntegerField(blank=True, help_text="Usuário que alterou")

    class Meta:
        db_table = 'parametrosmobile'
        unique_together = ('para_empr', 'para_fili', 'para_modu', 'para_nome')
        ordering = ['para_modu', 'para_nome']


class LogParametroSistema(models.Model):
    log_codi = models.AutoField(primary_key=True)
    log_tabe = models.CharField(max_length=50, help_text="Tabela alterada")
    log_regi = models.IntegerField(help_text="ID do registro")
    log_acao = models.CharField(max_length=20, choices=[
        ('create', 'Criação'),
        ('update', 'Alteração'),
        ('delete', 'Exclusão')
    ])
    log_valo_ante = models.BooleanField(null=True, blank=True, help_text="Valor anterior")
    log_valo_novo = models.BooleanField(null=True, blank=True, help_text="Valor novo")
    log_usua = models.IntegerField(help_text="Usuário")
    log_data = models.DateTimeField(auto_now_add=True)
    log_ip = models.GenericIPAddressField(blank=True, null=True, help_text="IP do usuário")

    class Meta:
        db_table = 'log_parametro_sistema'
        verbose_name = 'Log de Parâmetro'
        verbose_name_plural = 'Logs de Parâmetros'
        ordering = ['-log_data']

    def __str__(self):
        return f"{self.log_acao} - {self.log_tabe} ({self.log_data})"
