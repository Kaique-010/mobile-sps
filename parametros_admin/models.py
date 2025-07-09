from django.db import models
import json
from django.core.exceptions import ValidationError
from django.utils import timezone



class Modulo(models.Model):
    """Módulos do sistema"""
    modu_codi = models.AutoField(primary_key=True)
    modu_nome = models.CharField(max_length=50, unique=True, help_text="Nome do módulo")
    modu_desc = models.TextField(help_text="Descrição do módulo")
    modu_ativ = models.BooleanField(default=True, help_text="Módulo ativo no sistema")
    modu_icone = models.CharField(max_length=50, blank=True, help_text="Ícone do módulo")
    modu_ordem = models.IntegerField(default=0, help_text="Ordem de exibição")
    
    class Meta:
        db_table = 'modulosmobile'
        ordering = ['modu_ordem', 'modu_nome']


    
    
class PermissaoModulo(models.Model):
    """Permissões de módulos por empresa/filial"""
    perm_codi = models.AutoField(primary_key=True)
    perm_empr = models.IntegerField(help_text="Código da empresa")
    perm_fili = models.IntegerField(help_text="Código da filial")
    perm_modu = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='permissoes')
    perm_ativ = models.BooleanField(default=True, help_text="Módulo liberado")
    perm_usua_libe = models.CharField(max_length=150, blank=True, help_text="Usuário que liberou")
    
    class Meta:
        db_table = 'permissoesmodulosmobile'
        unique_together = ('perm_empr', 'perm_fili', 'perm_modu')

    
    def __str__(self):
        return f"{self.perm_modu.modu_nome} - Emp: {self.perm_empr}/Fil: {self.perm_fili}"
    







class ConfiguracaoEstoque(models.Model):
    """Configurações específicas de estoque"""
    conf_codi = models.AutoField(primary_key=True)
    conf_empr = models.IntegerField(help_text="Código da empresa")
    conf_fili = models.IntegerField(help_text="Código da filial")
    
    # Configurações de movimentação
    conf_pedi_move_esto = models.BooleanField(default=True, help_text="Pedidos movimentam estoque")
    conf_orca_move_esto = models.BooleanField(default=False, help_text="Orçamentos movimentam estoque")
    conf_os_move_esto = models.BooleanField(default=True, help_text="OS movimenta estoque")
    conf_prod_move_esto = models.BooleanField(default=True, help_text="Produção movimenta estoque")
    
    # Configurações de controle
    conf_esto_nega = models.BooleanField(default=False, help_text="Permite estoque negativo")
    conf_esto_mini = models.BooleanField(default=True, help_text="Controla estoque mínimo")
    conf_esto_maxi = models.BooleanField(default=False, help_text="Controla estoque máximo")
    
    # Configurações de custo
    conf_custo_medio = models.BooleanField(default=True, help_text="Usa custo médio")
    conf_custo_ulti = models.BooleanField(default=False, help_text="Usa último custo")
    
    # Auditoria
    conf_data_alte = models.DateTimeField(auto_now=True)
    conf_usua_alte = models.CharField(max_length=150, blank=True, help_text="Usuário que alterou")
    
    class Meta:
        db_table = 'conf_estoque_mobile'
        unique_together = ('conf_empr', 'conf_fili')
        verbose_name = 'Configuração de Estoque'
        verbose_name_plural = 'Configurações de Estoque'
    
    def __str__(self):
        return f"Config Estoque - Emp: {self.conf_empr}/Fil: {self.conf_fili}"



class ConfiguracaoFinanceiro(models.Model):
    """Configurações financeiras"""
    conf_codi = models.AutoField(primary_key=True)
    conf_empr = models.IntegerField(help_text="Código da empresa")
    conf_fili = models.IntegerField(help_text="Código da filial")
    
    # Configurações de pagamento
    conf_perm_desc_pedi = models.BooleanField(default=True, help_text="Permite desconto em pedidos")
    conf_desc_maxi_pedi = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Desconto máximo em pedidos (%)")
    conf_perm_acre_pedi = models.BooleanField(default=True, help_text="Permite acréscimo em pedidos")
    
    # Configurações de comissão
    conf_calc_comi_auto = models.BooleanField(default=True, help_text="Calcula comissão automaticamente")
    conf_comi_sobr_desc = models.BooleanField(default=False, help_text="Comissão sobre desconto")
    
    # Configurações de prazo
    conf_praz_maxi_vend = models.IntegerField(default=0, help_text="Prazo máximo para vendas (dias)")
    conf_perm_vend_praz = models.BooleanField(default=True, help_text="Permite vendas a prazo")
    
    # Auditoria
    conf_data_alte = models.DateTimeField(auto_now=True)
    conf_usua_alte = models.CharField(max_length=150, blank=True, help_text="Usuário que alterou")
    
    class Meta:
        db_table = 'conf_financeiro_mobile'
        unique_together = ('conf_empr', 'conf_fili')
        verbose_name = 'Configuração Financeira'
        verbose_name_plural = 'Configurações Financeiras'
    
    def __str__(self):
        return f"Config Financeiro - Emp: {self.conf_empr}/Fil: {self.conf_fili}"

class LogParametros(models.Model):
    """Log de alterações nos parâmetros"""
    log_codi = models.AutoField(primary_key=True)
    log_tabe = models.CharField(max_length=50, help_text="Tabela alterada")
    log_regi = models.IntegerField(help_text="ID do registro")
    log_acao = models.CharField(max_length=20, choices=[
        ('create', 'Criação'),
        ('update', 'Alteração'),
        ('delete', 'Exclusão')
    ])
    log_valo_ante = models.TextField(blank=True, help_text="Valor anterior (JSON)")
    log_valo_novo = models.TextField(blank=True, help_text="Valor novo (JSON)")
    log_usua = models.CharField(max_length=150, help_text="Usuário")
    log_data = models.DateTimeField(auto_now_add=True)
    log_ip = models.GenericIPAddressField(blank=True, null=True, help_text="IP do usuário")
    
    class Meta:
        db_table = 'log_parametro_mobile'
        verbose_name = 'Log de Parâmetro'
        verbose_name_plural = 'Logs de Parâmetros'
        ordering = ['-log_data']
    
    def __str__(self):
        return f"{self.log_acao} - {self.log_tabe} ({self.log_data})"
