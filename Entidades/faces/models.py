from Entidades.models import Entidades
from django.db import models
from django.contrib.postgres.fields import ArrayField


class EntidadesFaces(models.Model):
    # db_constraint=False pois a tabela 'entidades' em bancos legados pode não ter constraint UNIQUE/PK formal
    face_enti = models.ForeignKey(Entidades, on_delete=models.CASCADE, related_name='faces', db_constraint=False)
    face_embe = ArrayField(models.FloatField(), size=128, blank=True, null=True)
    face_data = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.face_enti.enti_nome
    class Meta:
        db_table = 'entidades_faces'
        managed = 'false'