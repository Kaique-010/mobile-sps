from rest_framework.exceptions import PermissionDenied


class EmprFiliMixin:
    empresa_field = 'enti_empr'
    filial_field = 'enti_fili'

    def get_queryset(self):
        request = self.request
        empresa_id = getattr(request, 'empresa_id', None)
        filial_id = getattr(request, 'filial_id', None)

        print('[MIXIN] Empresa ID recebido:', empresa_id)
        print('[MIXIN] Filial ID recebido:', filial_id)

        if empresa_id is None or filial_id is None:
            raise PermissionDenied('Empresa ou filial não informada no cabeçalho da requisição.')

        filtros = {
            self.empresa_field: empresa_id,
            self.filial_field: filial_id
        }
        return super().get_queryset().filter(**filtros)


class EmprFiliSaveMixin:
    empresa_field = 'enti_empr'
    filial_field = 'enti_fili'

    def perform_create(self, serializer):
        request = self.request
        empresa_id = getattr(request, 'empresa_id', None)
        filial_id = getattr(request, 'filial_id', None)

        print('[MIXIN] Empresa ID recebido:', empresa_id)
        print('[MIXIN] Filial ID recebido:', filial_id)

        if not empresa_id or not filial_id:
            raise PermissionDenied('Empresa ou filial não informada no cabeçalho da requisição.')

        save_kwargs = {
            self.empresa_field: empresa_id,
            self.filial_field: filial_id
        }
        serializer.save(**save_kwargs)