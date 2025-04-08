# auth/models.py
from django.db import models

class UCTabUsers(models.Model):
    uciduser = models.AutoField(primary_key=True)
    ucusername = models.CharField(max_length=150)
    uclogin = models.CharField(max_length=150)
    ucpassword = models.CharField(max_length=128)
    ucemail = models.EmailField(blank=True, null=True)

    class Meta:
        db_table = 'uctabusers'
        managed = False 
    
    @property
    def id(self):
        return self.uciduser