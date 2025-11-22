import os
from django.views import View
from django.http import HttpResponse, HttpResponseNotFound


class LogoView(View):
    def get(self, request, variation, codigo):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        path = os.path.join(base_dir, 'Logos', variation, f"{codigo}.bmp")
        try:
            with open(path, 'rb') as f:
                data = f.read()
            return HttpResponse(data, content_type='image/bmp')
        except Exception:
            return HttpResponseNotFound()
