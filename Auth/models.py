from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

class UCTabUsers(AbstractBaseUser, PermissionsMixin):
    uciduser = models.AutoField(primary_key=True)
    ucusername = models.CharField(max_length=150, unique=True)
    uclogin = models.CharField(max_length=150)
    ucpassword = models.CharField(max_length=128)
    ucemail = models.EmailField(blank=True, null=True)

    USERNAME_FIELD = 'ucusername'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'uctabusers'
        managed = False

    def __str__(self):
        return self.ucusername

    @property
    def id(self):
        return self.uciduser

    # 👇 ESSA LINHA FAZ O LOGIN FUNCIONAR
    @property
    def password(self):
        return self.ucpassword

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.ucpassword)
    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return False  # ou sua lógica aqui

    @property
    def is_superuser(self):
        return False  # ou sua lógica aqui

    @property
    def is_active(self):
        return True  # ou sua lógica aqui

    @property
    def last_login(self):
        return None  # Django exige isso
    
    


class Empresas(models.Model):
    empr_codi = models.AutoField(primary_key=True, db_column='empr_codi')
    empr_nome = models.CharField('Nome da Empresa', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ', max_length=14, unique=True, db_column='empr_cnpj')

    class Meta:
        db_table = 'empresas'

    def __str__(self):
        return self.empr_nome


class Filiais(models.Model):
    fili_id = models.AutoField(primary_key=True, db_column='fili_id')
    empr_codi = models.ForeignKey(Empresas, db_column='empr_codi', on_delete=models.CASCADE)
    empr_nome = models.CharField('Nome da Filial', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ da Filial', max_length=14, unique=True, db_column='empr_cnpj')

    class Meta:
        db_table = 'filiais'

    def __str__(self):
        return self.empr_nome


class UserEmpresaFilial(models.Model):
    user = models.ForeignKey(UCTabUsers, related_name="empresas_filiais", on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresas, related_name="usuarios_empresas", on_delete=models.CASCADE)
    filial = models.ForeignKey(Filiais, related_name="usuarios_filiais", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'empresa', 'filial')
        db_table = 'user_empresa_filial'