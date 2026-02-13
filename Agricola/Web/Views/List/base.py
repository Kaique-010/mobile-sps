from django.views.generic import ListView
from core.utils import get_licenca_db_config
import logging

logger = logging.getLogger(__name__)

class BaseListView(ListView):
    model = None
    template_name = None
    context_object_name = None
    empresa_field = None
    filial_field = None
    order_by_field = 'id'
    
    def get_queryset(self):
        try:
            db_name = get_licenca_db_config(self.request) or 'default'
            # Log apenas em debug para não poluir
            if self.request.GET:
                 logger.info(f"[BaseListView] {self.model.__name__} filtering. DB: {db_name}, User: {self.request.user}, GET: {self.request.GET}")
            
            queryset = self.model.objects.using(db_name).all()
            
            if self.empresa_field and self.filial_field:
                empresa = getattr(self.request.user, 'empresa', None) or self.request.session.get('empresa_id', 1)
                filial = getattr(self.request.user, 'filial', None) or self.request.session.get('filial_id', 1)
                
                filters = {
                    self.empresa_field: empresa,
                    self.filial_field: filial
                }
                queryset = queryset.filter(**filters)
                
            if self.order_by_field:
                queryset = queryset.order_by(self.order_by_field)
                
            return queryset[:100]
        except Exception as e:
            logger.error(f"[BaseListView] Erro no get_queryset: {e}", exc_info=True)
            raise e
