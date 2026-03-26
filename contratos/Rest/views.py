from rest_framework import viewsets
from ..service import ContratoService
from ..models import Contratosvendas
from ..Rest.serializers import ContratosvendasSerializer
from core.utils import get_db_from_slug




class ContratoViewSet(viewsets.ModelViewSet):
    serializer_class = ContratosvendasSerializer
    search_fields = ['cont_cont', 'cont_clie__enti_nome', 'cont_empr__emp_nome']
    
    def get_queryset(self):
        banco = get_db_from_slug(self.request)
        return Contratosvendas.objects.using(banco).all().order_by("cont_cont")
    
    def create(self, request, *args, **kwargs):
        context = self.get_serializer_context()

        contrato = ContratoService.create_contrato(request.data, context)

        serializer = self.get_serializer(contrato)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        context = self.get_serializer_context()

        contrato = ContratoService.update_contrato(instance.cont_cont, request.data, context)
    
        serializer = self.get_serializer(contrato)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        banco = get_db_from_slug(self.request)

        try:
            ContratoService.delete_contrato(instance.cont_cont, banco)
            return Response(status=204)
        except Exception as e:
            return Response({"error": str(e)}, status=400)