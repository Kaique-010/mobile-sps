from django.apps import AppConfig


class AgricolaConfig(AppConfig):
    name = 'Agricola'
    verbose_name = 'Agricola'
    
    def ready(self):
        import Agricola.signals