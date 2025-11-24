from rest_framework.response import Response


def handle_retrieve(viewset, request):
    instance = viewset.get_object()
    serializer = viewset.get_serializer(instance)
    return Response(serializer.data)