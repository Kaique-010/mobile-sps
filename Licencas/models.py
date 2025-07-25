from django.db import models
import json
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password as django_check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager



class UsuariosManager(BaseUserManager):
    def get_by_natural_key(self, username):
        return self.get(usua_nome=username)

    def create_user(self, usua_nome, password=None, **extra_fields):
        if not usua_nome:
            raise ValueError("O campo 'usua_nome' é obrigatório")

        # Remove campos que o model não suporta (do legado)
        extra_fields.pop('is_superuser', None)
        extra_fields.pop('is_staff', None)
        extra_fields.pop('is_active', None)

        user = self.model(usua_nome=usua_nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usua_nome, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(usua_nome, password, **extra_fields)


class Usuarios(AbstractBaseUser, PermissionsMixin):
    usua_codi = models.AutoField(primary_key=True)
    usua_nome = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, db_column='usua_senh_mobi')
    usua_seto = models.IntegerField(db_column='usua_seto') 
    USERNAME_FIELD = 'usua_nome'
    PASSWORD_FIELD = 'password'
    REQUIRED_FIELDS = []

    objects = UsuariosManager()

    class Meta:
        db_table = 'usuarios'
        managed = False

    def __str__(self):
        return self.usua_nome

    def check_password(self, raw_password):
        
        if not self.password:
            return False
        password_stripped = self.password.strip()
        if password_stripped.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            try:
                return django_check_password(raw_password, password_stripped)
            except:
                return False
        else:
            return password_stripped == raw_password

    def set_password(self, raw_password):
       
        self.password = raw_password
        self._password = raw_password



    def atualizar_senha(self, nova_senha):
       
        from .utils import atualizar_senha
        return atualizar_senha(self.usua_nome, nova_senha)

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return True  # ou coloque uma lógica se quiser restringir

    @property
    def is_superuser(self):
        return True  # idem, pode colocar regra

    @property
    def is_active(self):
        return True

    @property
    def last_login(self):
        return None
    
    @property
    def setor(self):
        from OrdemdeServico.models import OrdemServicoFaseSetor 
        try:
            return OrdemServicoFaseSetor.objects.get(osfs_codi=self.usua_seto)
        except OrdemServicoFaseSetor.DoesNotExist:
            return None

# ---- Classes auxiliares ----

class Empresas(models.Model):
    empr_codi = models.AutoField(primary_key=True, db_column='empr_codi')
    empr_nome = models.CharField('Nome da Empresa', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ', max_length=14, unique=True, db_column='empr_cnpj')

    class Meta:
        db_table = 'empresas'
        managed = False

    def __str__(self):
        return self.empr_nome


class Filiais(models.Model):
    empr_empr = models.IntegerField(primary_key=True, db_column='empr_empr')
    empr_codi = models.ForeignKey(Empresas, db_column='empr_codi', on_delete=models.CASCADE)
    empr_nome = models.CharField('Nome da Filial', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ da Filial', max_length=14, unique=True, db_column='empr_cnpj')

    class Meta:
        db_table = 'filiais'
        managed = False

    def __str__(self):
        return self.empr_nome


class Licencas(models.Model):
    lice_id = models.AutoField(primary_key=True)
    lice_docu = models.CharField(max_length=14, unique=True)
    lice_nome = models.CharField(max_length=100)
    lice_emai = models.EmailField(blank=True, null=True)
    lice_bloq = models.BooleanField(default=False)
    lice_nume_empr = models.IntegerField()
    lice_nume_fili = models.IntegerField()
    #lice_modu_libe = models.TextField(default="{}")
    _log_data = models.DateField(blank=True, null=True) 
    _log_time = models.TimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'licencas'

    def get_modu_libe(self):
        return json.loads(self.lice_modu_libe or "{}")

    def set_modu_libe(self, data):
        self.lice_modu_libe = json.dumps(data)