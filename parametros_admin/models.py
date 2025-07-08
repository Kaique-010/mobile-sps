from django.db import models
import json
from django.core.exceptions import ValidationError

class ParametrosGerais(models.Model):
    """Configurações gerais do sistema"""
    para_codi = models.AutoField(primary_key=True)
    para_empr = models.IntegerField(help_text="Código da empresa")
    para_fili = models.IntegerField(help_text="Código da filial")
    para_nome = models.CharField(max_length=100, help_text="Nome do parâmetro")
    para_valo = models.TextField(help_text="Valor do parâmetro (JSON)")
    para_desc = models.TextField(blank=True, help_text="Descrição do parâmetro")
    para_tipo = models.CharField(max_length=20, choices=[
        ('string', 'Texto'),
        ('boolean', 'Verdadeiro/Falso'),
        ('integer', 'Número Inteiro'),
        ('decimal', 'Número Decimal'),
        ('json', 'JSON')
    ], default='string')
    para_ativ = models.BooleanField(default=True, help_text="Parâmetro ativo")
    para_data_cria = models.DateTimeField(auto_now_add=True)
    para_data_alte = models.DateTimeField(auto_now=True)
    para_usua_alte = models.CharField(max_length=150, blank=True, help_text="Usuário que alterou")
    
    class Meta:
        db_table = 'param_geral_mobile'
        unique_together = ('para_empr', 'para_fili', 'para_nome')
        verbose_name = 'Parâmetro Geral'
        verbose_name_plural = 'Parâmetros Gerais'
    
    def __str__(self):
        return f"{self.para_nome} - Emp: {self.para_empr}/Fil: {self.para_fili}"
    
    def get_valor_typed(self):
        """Retorna o valor convertido para o tipo correto"""
        try:
            if self.para_tipo == 'boolean':
                return self.para_valo.lower() in ['true', '1', 'sim', 'yes']
            elif self.para_tipo == 'integer':
                return int(self.para_valo)
            elif self.para_tipo == 'decimal':
                return float(self.para_valo)
            elif self.para_tipo == 'json':
                return json.loads(self.para_valo)
            else:
                return self.para_valo
        except (ValueError, json.JSONDecodeError):
            return self.para_valo

class PermissoesModulos(models.Model):
    """Controle de módulos por empresa/filial"""
    perm_codi = models.AutoField(primary_key=True)
    perm_empr = models.IntegerField(help_text="Código da empresa")
    perm_fili = models.IntegerField(help_text="Código da filial")
    perm_modu = models.CharField(max_length=50, help_text="Nome do módulo")
    perm_ativ = models.BooleanField(default=True, help_text="Módulo ativo")
    perm_data_libe = models.DateTimeField(auto_now_add=True, help_text="Data de liberação")
    perm_data_venc = models.DateTimeField(null=True, blank=True, help_text="Data de vencimento")
    perm_usua_libe = models.CharField(max_length=150, blank=True, help_text="Usuário que liberou")
    perm_obse = models.TextField(blank=True, help_text="Observações")
    
    class Meta:
        db_table = 'perm_modulo_mobile'

        unique_together = ('perm_empr', 'perm_fili', 'perm_modu')
        verbose_name = 'Permissão de Módulo'
        verbose_name_plural = 'Permissões de Módulos'
    
    def __str__(self):
        return f"{self.perm_modu} - Emp: {self.perm_empr}/Fil: {self.perm_fili}"
    
    @property
    def is_vencido(self):
        if not self.perm_data_venc:
            return False
        from django.utils import timezone
        return timezone.now() > self.perm_data_venc

class PermissoesRotas(models.Model):
    """Controle granular de rotas/screens"""
    rota_codi = models.AutoField(primary_key=True)
    rota_empr = models.IntegerField(help_text="Código da empresa")
    rota_fili = models.IntegerField(help_text="Código da filial")
    rota_modu = models.CharField(max_length=50, help_text="Módulo")
    rota_nome = models.CharField(max_length=100, help_text="Nome da rota")
    rota_path = models.CharField(max_length=200, help_text="Path da rota")
    rota_tipo = models.CharField(max_length=20, choices=[
        ('list', 'Apenas Listagem'),
        ('read', 'Leitura'),
        ('create', 'Criação'),
        ('update', 'Edição'),
        ('delete', 'Exclusão'),
        ('full', 'CRUD Completo')
    ], default='read')
    rota_ativ = models.BooleanField(default=True, help_text="Rota ativa")
    rota_data_cria = models.DateTimeField(auto_now_add=True)
    rota_usua_cria = models.CharField(max_length=150, blank=True, help_text="Usuário que criou")
    rota_tela = models.CharField(max_length=100, help_text="Nome da tela/componente")
    rota_acao = models.CharField(max_length=20, choices=[
        ('create', 'Criar'),
        ('read', 'Visualizar'),
        ('update', 'Editar'),
        ('delete', 'Excluir'),
        ('export', 'Exportar'),
        ('import', 'Importar')
    ])
    
    class Meta:
        db_table = 'perm_rota_mobile'
        unique_together = ('rota_empr', 'rota_fili', 'rota_modu', 'rota_nome')
        verbose_name = 'Permissão de Rota'
        verbose_name_plural = 'Permissões de Rotas'
    
    def __str__(self):
        return f"{self.rota_nome} ({self.rota_tipo}) - {self.rota_modu}"

class ConfiguracaoEstoque(models.Model):
    """Configurações  estoque"""
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
