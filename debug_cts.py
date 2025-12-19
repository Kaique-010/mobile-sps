
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType

print("Listing ContentTypes matching 'dash':")
cts = ContentType.objects.filter(app_label__icontains='dash') | ContentType.objects.filter(model__icontains='dash')
for ct in cts:
    print(f"ID: {ct.id}, App: {ct.app_label}, Model: {ct.model}")

from perfilweb.models import PermissaoPerfil

print("\nListing PermissaoPerfil for app 'dash':")
perms = PermissaoPerfil.objects.filter(perf_ctype__app_label='dash')
for p in perms:
    print(f"Perfil: {p.perf_perf.perf_nome}, Model: {p.perf_ctype.model}, Acao: {p.perf_acao}")
