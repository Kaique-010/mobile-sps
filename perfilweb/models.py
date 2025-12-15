from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from Licencas.models import Usuarios


class Perfil(models.Model):
    perf_nome = models.CharField(max_length=100, unique=True)
    perf_ativ = models.BooleanField(default=True)

    class Meta:
        db_table = 'perfil'

    def __str__(self):
        return self.perf_nome


class UsuarioPerfil(models.Model):
    perf_usua = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    perf_perf = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    perf_ativ = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario_perfil'
        unique_together = ('perf_usua', 'perf_perf')


class PerfilHeranca(models.Model):
    perf_filho = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='perf_pais_rel')
    perf_pai = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name='perf_filhos_rel')

    class Meta:
        db_table = 'perfil_heranca'
        unique_together = ('perf_filho', 'perf_pai')


class PermissaoPerfil(models.Model):
    perf_perf = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    perf_ctype = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    perf_acao = models.CharField(max_length=30)

    class Meta:
        db_table = 'permissao_perfil'
        unique_together = ('perf_perf', 'perf_ctype', 'perf_acao')


class PermissaoLog(models.Model):
    perf_perf = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    perf_ctype = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    perf_acao = models.CharField(max_length=30)
    perf_oper = models.ForeignKey(Usuarios, on_delete=models.SET_NULL, null=True, blank=True)
    perf_data = models.DateTimeField(auto_now_add=True)
    perf_op = models.CharField(max_length=20)

    class Meta:
        db_table = 'permissao_log'
