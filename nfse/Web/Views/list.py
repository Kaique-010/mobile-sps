from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import View, ListView

from core.mixin import DBAndSlugMixin
from nfse.models import Nfse

class NfseListView(DBAndSlugMixin, ListView):
    template_name = 'nfse/list.html'
    context_object_name = 'notas'

    def get_queryset(self):
        return (
            Nfse.objects.using(self.request.db_alias)
            .filter(
                nfse_empr=self.empresa_id,
                nfse_fili=self.filial_id
            )
            .order_by('-nfse_id')
        )

    

