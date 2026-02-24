from django.db import models


class LicencaWeb(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    cnpj = models.CharField(max_length=20)
    db_name = models.CharField(max_length=100)
    db_host = models.CharField(max_length=200)
    db_port = models.CharField(max_length=10)
    modulos = models.TextField(default='[]', blank=True)

    db_user = models.CharField(max_length=128, blank=True, default='')
    db_password = models.CharField(max_length=256, blank=True, default='')
    plano = models.OneToOneField('planos.Plano', on_delete=models.SET_NULL, null=True, blank=True, related_name='licenca_web', db_column='plano_id')

    class Meta:
        verbose_name = 'Licença Web'
        verbose_name_plural = 'Licenças Web'
        db_table = 'licencas_web'

    def __str__(self):
        return f"{self.slug} ({self.db_name})"
