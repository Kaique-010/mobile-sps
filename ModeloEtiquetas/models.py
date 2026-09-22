from django.db import models
from django.contrib.postgres.fields import JSONField

class ModeloEtiqueta(models.Model):

    Tipo_Papel = (
        ("A4", "Folha A4"),
        ("BOBINA", "Bobina"),
    )

    Orientacao = (
        ("vertical", "Vertical"),
        ("horizontal", "Horizontal"),
    )

    nome = models.CharField(max_length=100)

    empresa_id = models.CharField(max_length=50)
    filial_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    tipo_papel = models.CharField(
        max_length=10,
        choices=Tipo_Papel,
        default=Tipo_Papel[0][0],
    )
    orientacao = models.CharField(
        max_length=15,
        choices=Orientacao,
        default=Orientacao[0][0],
    )

    largura_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=40,
    )

    altura_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=60,
    )

    colunas = models.PositiveSmallIntegerField(default=1)
    linhas = models.PositiveSmallIntegerField(default=1)

    margem_superior_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    margem_inferior_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    margem_esquerda_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    margem_direita_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    espacamento_horizontal_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=2,
    )

    espacamento_vertical_mm = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=2,
    )

    configuracao = JSONField(default=dict, blank=True)

    padrao = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "produtos_modelo_etiqueta"
        ordering = ["nome"]

    def __str__(self):
        return self.nome