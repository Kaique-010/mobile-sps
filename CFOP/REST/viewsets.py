from rest_framework import status, viewsets
from rest_framework.response import Response
from django.db.models import Q
from core.utils import get_licenca_db_config
from ..models import CFOP
from .serializers import CFOPSerializer


class CFOPViewSet(viewsets.ModelViewSet):
    serializer_class = CFOPSerializer
    lookup_value_regex = r"\d+"

    def get_banco(self):
        return get_licenca_db_config(self.request) or "default"

    def get_empresa_id(self):
        return (
            self.request.query_params.get("empresa_id")
            or self.request.headers.get("X-Empresa")
            or self.request.session.get("empresa_id")
            or self.request.headers.get("Empresa_id")
        )

    def get_queryset(self):
        banco = self.get_banco()
        empresa_id = self.get_empresa_id()
        q = self.request.query_params.get("q", "").strip()

        qs = CFOP.objects.using(banco).all()

        if empresa_id:
            try:
                qs = qs.filter(cfop_empr=int(empresa_id))
            except Exception:
                pass

        if q:
            qs = qs.filter(Q(cfop_codi__icontains=q) | Q(cfop_desc__icontains=q))

        return qs.order_by("cfop_codi")

    def list(self, request, *args, **kwargs):
        if str(request.query_params.get("select") or "").strip() in ("1", "true", "True"):
            banco = self.get_banco()
            empresa_id = self.get_empresa_id()
            q = request.query_params.get("q", "").strip()

            qs = CFOP.objects.using(banco).all()
            if empresa_id:
                try:
                    qs = qs.filter(cfop_empr=int(empresa_id))
                except Exception:
                    pass

            if q:
                qs = qs.filter(Q(cfop_codi__icontains=q) | Q(cfop_desc__icontains=q))

            qs = qs.only("cfop_id", "cfop_codi", "cfop_desc").order_by("cfop_codi")[:20]

            return Response(
                [{"value": str(x.cfop_id), "label": f"{x.cfop_codi} • {x.cfop_desc}"} for x in qs]
            )

        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        banco = self.get_banco()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = dict(serializer.validated_data)
        empresa_id = self.get_empresa_id()
        if empresa_id:
            try:
                data["cfop_empr"] = int(empresa_id)
            except Exception:
                pass

        obj = CFOP.objects.using(banco).create(**data)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        banco = self.get_banco()
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        empresa_id = self.get_empresa_id()
        if empresa_id:
            try:
                setattr(instance, "cfop_empr", int(empresa_id))
            except Exception:
                pass

        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)

        instance.save(using=banco)
        return Response(self.get_serializer(instance).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.delete(using=self.get_banco())
