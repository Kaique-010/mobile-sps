from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import LicencaWeb
from .serializers import LicencaWebSerializer


@api_view(['GET'])
def licencas_web_mapa(request):
    qs = LicencaWeb.objects.all().order_by('slug')
    data = LicencaWebSerializer(qs, many=True).data
    return Response(data)

