
from django.db import models
from Licencas.models import Usuarios

class OnboardingStepProgress(models.Model):
    usuario = models.ForeignKey(Usuarios, on_delete=models.CASCADE)
    empr_id = models.IntegerField()
    step_slug = models.CharField(max_length=50)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "empr_id", "step_slug")
        db_table = "onboarding_step_progress"

