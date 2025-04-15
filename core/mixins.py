class EmprFiliMixin:
    empresa_field = 'enti_empr'
    filial_field = 'enti_fili'
    
    def get_queryset(self):
        user = self.request.user
        empresa_id = getattr(user, 'empresa_id', None)
        filial_id = getattr(user, 'filial_id', None)
        
        if not empresa_id or not filial_id:
            return self.queryset.none()
        
        filtros = {
            self.empresa_field: empresa_id,
            self.filial_field: filial_id            
        }
        return self.queryset.filter(**filtros)


class EmprFiliSaveMixin:
    empresa_field = 'enti_empr'
    filial_field = 'enti_fili'

    def perform_create(self, serializer):
        user = self.request.user
        empresa_id = getattr(user, 'empresa_id', None)
        filial_id = getattr(user, 'filial_id', None)

        save_kwargs = {
            self.empresa_field: empresa_id,
            self.filial_field: filial_id
        }
        serializer.save(**save_kwargs)
