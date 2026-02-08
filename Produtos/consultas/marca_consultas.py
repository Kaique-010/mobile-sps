from ..models import Marca

def listar_marcas(banco):
    if banco:
        return Marca.objects.using(banco).all().order_by('nome')
    return Marca.objects.none()
