from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect


class SPSViewMixin:
    """
    Mixin simples para facilitar mensagens e redirecionamento.
    """

    success_message = None
    success_url_name = None

    def form_success(self, msg=None):
        if msg or self.success_message:
            messages.success(self.request, msg or self.success_message)
        return redirect(self.get_success_url())

    def get_success_url(self):
        if not self.success_url_name:
            raise Exception("Defina success_url_name na view")
        return reverse(self.success_url_name)
