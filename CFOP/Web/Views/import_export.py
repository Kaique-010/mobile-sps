import csv
from io import StringIO
from django.views import View
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from core.utils import get_licenca_db_config
from ...models import CFOP

class CFOPExportView(View):
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        return super().dispatch(request, *args, **kwargs)
    def get(self, request, *args, **kwargs):
        qs = CFOP.objects.using(self.db_alias).all()
        if self.empresa_id:
            qs = qs.filter(cfop_empr=int(self.empresa_id))
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(['cfop_empr','cfop_codi','cfop_cfop','cfop_desc'])
        for o in qs.order_by('cfop_codi'):
            w.writerow([o.cfop_empr,o.cfop_codi,o.cfop_cfop,o.cfop_desc])
        resp = HttpResponse(buf.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="cfop.csv"'
        return resp

class CfopImportView(View):
    template_name = 'CFOP/cfop_import.html'
    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs.get('slug')
        self.db_alias = get_licenca_db_config(request)
        self.empresa_id = request.session.get('empresa_id') or request.headers.get('X-Empresa') or request.GET.get('empresa')
        return super().dispatch(request, *args, **kwargs)
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'slug': self.slug})
    def post(self, request, *args, **kwargs):
        f = request.FILES.get('file')
        if not f:
            messages.error(request, 'Arquivo ausente')
            return render(request, self.template_name, {'slug': self.slug})
        c = f.read().decode('utf-8').splitlines()
        r = csv.DictReader(c)
        count = 0
        for row in r:
            empr = int(row.get('cfop_empr') or self.empresa_id or 0)
            codi = int(row.get('cfop_codi') or 0)
            cfopv = int(row.get('cfop_cfop') or 0)
            desc = (row.get('cfop_desc') or '').strip()
            if not codi:
                continue
            obj = Cfop.objects.using(self.db_alias).filter(cfop_empr=empr, cfop_codi=codi).first()
            if obj:
                obj.cfop_cfop = cfopv
                obj.cfop_desc = desc
                obj.save(using=self.db_alias)
            else:
                obj = Cfop(cfop_empr=empr, cfop_codi=codi, cfop_cfop=cfopv, cfop_desc=desc)
                obj.save(using=self.db_alias)
            count += 1
        messages.success(request, f'Importados {count}')
        return redirect(f"/web/{self.slug}/cfop/")