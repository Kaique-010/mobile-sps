from django.db import models
from django.conf import settings
# Removido JSONField para evitar erro de encoding no PostgreSQL ao salvar com caracteres Unicode

class LogAcao(models.Model):
    TIPO_ACAO_CHOICES = [
        ('GET', 'Consulta'),
        ('POST', 'Criação'),
        ('PUT', 'Atualização'),
        ('PATCH', 'Atualização Parcial'),
        ('DELETE', 'Exclusão'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo_acao = models.CharField(max_length=10, choices=TIPO_ACAO_CHOICES)
    url = models.TextField()
    ip = models.GenericIPAddressField(null=True)
    navegador = models.CharField(max_length=255)
    # Alteração: JSONField -> TextField para armazenar JSON serializado manualmente (ensure_ascii=False)
    dados = models.TextField(null=True, blank=True)  # Dados da requisição original (JSON string)
    dados_antes = models.TextField(null=True, blank=True)  # Estado anterior do objeto (JSON string)
    dados_depois = models.TextField(null=True, blank=True)  # Estado posterior do objeto (JSON string)
    campos_alterados = models.TextField(null=True, blank=True)  # Lista de campos modificados (JSON string)
    objeto_id = models.CharField(max_length=100, null=True, blank=True)  # ID do objeto alterado
    modelo = models.CharField(max_length=100, null=True, blank=True)  # Nome do modelo
    empresa = models.CharField(max_length=100, null=True, db_index=True)
    licenca = models.CharField(max_length=100, null=True, db_index=True)

    class Meta:
        db_table = 'auditoria_logacao'
        ordering = ['-data_hora']
        verbose_name = 'Log de Ação'
        verbose_name_plural = 'Logs de Ações'
        indexes = [
            models.Index(fields=['empresa', 'licenca', 'data_hora']),
            models.Index(fields=['usuario', 'data_hora']),
            models.Index(fields=['modelo', 'objeto_id']),
            models.Index(fields=['tipo_acao', 'data_hora']),
        ]

    def __str__(self):
        if self.modelo and self.objeto_id:
            return f"{self.empresa} - {self.usuario} - {self.get_tipo_acao_display()} - {self.modelo}#{self.objeto_id} - {self.data_hora}"
        return f"{self.empresa} - {self.usuario} - {self.get_tipo_acao_display()} - {self.data_hora}"

    @property
    def acao_formatada(self):
        return self.get_tipo_acao_display()
    
    @property
    def tem_alteracoes(self):
        """Verifica se há alterações registradas"""
        return bool(self.campos_alterados)
    
    @property
    def resumo_alteracoes(self):
        """Retorna um resumo das alterações realizadas"""
        if not self.campos_alterados:
            return None
        
        # Quando armazenado como string JSON, apenas retorna a string
        return str(self.campos_alterados)
    
    def get_objeto_info(self):
        """Retorna informações do objeto alterado"""
        if self.modelo and self.objeto_id:
            return f"{self.modelo} (ID: {self.objeto_id})"
        return None