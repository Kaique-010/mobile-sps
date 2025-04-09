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