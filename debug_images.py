
from OrdemdeServico.models import Ordemservicoimgantes, Ordemservicoimgdurante, Ordemservicoimgdepois
from django.conf import settings

def check_images(orde_nume):
    databases = list(settings.DATABASES.keys())
    print(f"Checking databases: {databases}")
    
    for db in databases:
        try:
            count_antes = Ordemservicoimgantes.objects.using(db).filter(iman_orde=orde_nume).count()
            count_durante = Ordemservicoimgdurante.objects.using(db).filter(imdu_orde=orde_nume).count()
            count_depois = Ordemservicoimgdepois.objects.using(db).filter(imde_orde=orde_nume).count()
            
            if count_antes > 0 or count_durante > 0 or count_depois > 0:
                print(f"FOUND in DB '{db}': Antes={count_antes}, Durante={count_durante}, Depois={count_depois}")
            else:
                # print(f"Not found in DB '{db}'")
                pass
        except Exception as e:
            print(f"Error accessing DB '{db}': {e}")

check_images(115460)
