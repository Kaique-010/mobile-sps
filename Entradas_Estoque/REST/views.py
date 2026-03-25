from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view
from core.decorator import modulo_necessario, ModuloRequeridoMixin
from core.registry import get_licenca_db_config
from ..models import EntradaEstoque
from .serializers import EntradasEstoqueSerializer
from parametros_admin.utils_estoque import  verificar_estoque_negativo
from parametros_admin.decorators import parametros_estoque_completo



import logging

logger = logging.getLogger(__name__)



class EntradasEstoqueViewSet(ModuloRequeridoMixin, ModelViewSet):
    modulo_necessario = 'Entradas_Estoque'
    permission_classes = [IsAuthenticated]
    serializer_class = EntradasEstoqueSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['entr_enti', 'entr_prod']
    filterset_fields = ['entr_empr', 'entr_fili']

    def get_queryset(self): 
        banco = get_licenca_db_config(self.request)
        
        if banco:
            return EntradaEstoque.objects.using(banco).all().order_by('-entr_sequ')
        else:           
            logger.error("Banco de dados não encontrado.")
            raise NotFound("Banco de dados não encontrado.")
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context

    def _merge_context_fields(self, request):
        raw = request.data
        try:
            data = raw.copy()
        except Exception:
            try:
                data = dict(raw)
            except Exception:
                data = {}

        def pick(*keys):
            for k in keys:
                v = data.get(k)
                if v is not None and str(v) != '':
                    return v
            return None

        if data.get('entr_empr') in (None, ''):
            data['entr_empr'] = pick('empresa_id', 'empr') or request.headers.get('X-Empresa')
        if data.get('entr_fili') in (None, ''):
            data['entr_fili'] = pick('filial_id', 'fili') or request.headers.get('X-Filial')
        if data.get('entr_usua') in (None, ''):
            usuario_id = pick('entr_usuario_id', 'usuario_id', 'usua')
            if usuario_id is None:
                user = getattr(request, 'user', None)
                usuario_id = (
                    getattr(user, 'usua_codi', None)
                    or getattr(user, 'id', None)
                    or getattr(user, 'pk', None)
                )
            data['entr_usua'] = usuario_id

        return data
        

    @parametros_estoque_completo(operacao='entrada')
    def create(self, request, *args, **kwargs):
        from django.db import models
        from decimal import Decimal
        import re
        db_alias = getattr(request, 'db_alias', get_licenca_db_config(request) or 'default')
        serializer = self.get_serializer(data=self._merge_context_fields(request))
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic(using=db_alias):
                banco = db_alias
                empresa_id = getattr(request, 'empresa_id', None) or serializer.validated_data.get('entr_empr') or 1
                filial_id = getattr(request, 'filial_id', None) or serializer.validated_data.get('entr_fili') or 1
                max_sequ = EntradaEstoque.objects.using(banco).aggregate(models.Max('entr_sequ'))['entr_sequ__max'] or 0
                data = serializer.validated_data
                entr_sequ = data.get('entr_sequ') or (max_sequ + 1)
                instance = serializer.save(entr_sequ=entr_sequ)
                auto_lote = bool(request.data.get('auto_lote'))
                atualizar_preco = bool(request.data.get('atualizar_preco', True))
                lote_texto = (request.data.get('entr_lote_vend') or '').strip() if isinstance(request.data.get('entr_lote_vend'), str) else ''
                lote_label = lote_texto if (lote_texto and not lote_texto.isdigit()) else None
                if not getattr(instance, 'entr_lote_vend', None) and lote_texto and not re.search(r'\d', lote_texto):
                    from Produtos.models import Lote
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(instance.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    novo = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=instance.pk).update(entr_lote_vend=int(novo))
                    instance.entr_lote_vend = int(novo)
                elif auto_lote and not getattr(instance, 'entr_lote_vend', None):
                    from Produtos.models import Lote
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(instance.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    novo = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=instance.pk).update(entr_lote_vend=int(novo))
                    instance.entr_lote_vend = int(novo)
                if getattr(instance, 'entr_lote_vend', None):
                    from Produtos.models import Lote
                    lote_num = int(instance.entr_lote_vend)
                    lote_data_fabr = request.data.get('lote_data_fabr') or instance.entr_data
                    lote_data_vali = request.data.get('lote_data_vali')
                    try:
                        if lote_data_fabr and not hasattr(lote_data_fabr, 'year'):
                            from datetime import date
                            lote_data_fabr = date.fromisoformat(str(lote_data_fabr))
                    except Exception:
                        lote_data_fabr = instance.entr_data
                    try:
                        if lote_data_vali and not hasattr(lote_data_vali, 'year'):
                            from datetime import date
                            lote_data_vali = date.fromisoformat(str(lote_data_vali))
                    except Exception:
                        lote_data_vali = None
                    lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(instance.entr_prod), lote_lote=lote_num)
                        .first()
                    )
                    if not lote:
                        from decimal import Decimal as D
                        lote = Lote(
                            lote_empr=int(empresa_id),
                            lote_prod=str(instance.entr_prod),
                            lote_lote=lote_num,
                            lote_unit=D(str(getattr(instance, 'entr_unit', 0) or 0)),
                            lote_sald=D('0.00'),
                            lote_data_fabr=lote_data_fabr,
                            lote_data_vali=lote_data_vali,
                            lote_ativ=True,
                            lote_obse=lote_label,
                        )
                    elif lote_label and not getattr(lote, 'lote_obse', None):
                        lote.lote_obse = lote_label
                    if lote_data_fabr is not None:
                        lote.lote_data_fabr = lote_data_fabr
                    if lote_data_vali is not None:
                        lote.lote_data_vali = lote_data_vali
                    saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                    qtd = Decimal(str(getattr(instance, 'entr_quan', 0) or 0))
                    lote.lote_sald = (saldo_atual + qtd).quantize(Decimal('0.01'))
                    lote.save(using=banco)
                if atualizar_preco:
                    from Produtos.models import Tabelaprecos
                    update_fields = {
                        'tabe_cuge': Decimal(str(getattr(instance, 'entr_unit', 0) or 0)).quantize(Decimal('0.01')),
                        'tabe_entr': getattr(instance, 'entr_data', None),
                    }
                    preco_vista = request.data.get('preco_vista')
                    preco_prazo = request.data.get('preco_prazo')
                    if preco_vista is not None and str(preco_vista) != '':
                        update_fields['tabe_avis'] = Decimal(str(preco_vista)).quantize(Decimal('0.01'))
                    if preco_prazo is not None and str(preco_prazo) != '':
                        update_fields['tabe_apra'] = Decimal(str(preco_prazo)).quantize(Decimal('0.01'))
                    qs = Tabelaprecos.objects.using(banco).filter(
                        tabe_empr=int(empresa_id),
                        tabe_fili=int(filial_id),
                        tabe_prod=str(instance.entr_prod),
                    )
                    updated = qs.update(**update_fields)
                    if not updated:
                        create_fields = {
                            'tabe_empr': int(empresa_id),
                            'tabe_fili': int(filial_id),
                            'tabe_prod': str(instance.entr_prod),
                            **update_fields,
                        }
                        Tabelaprecos.objects.using(banco).create(**create_fields)
                out = self.get_serializer(instance)
                return Response(out.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            logger.error(f"IntegrityError: {e}")
            raise ValidationError({"detail": "Erro de integridade no banco de dados."})
   
   
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"🗑️ [VIEW DELETE] Solicitada exclusão do ID {instance.entr_sequ}")
        try:
            db_alias = getattr(request, 'db_alias', 'default')
            with transaction.atomic(using=db_alias):
                instance.delete()
            logger.info(f"🗑️ [VIEW DELETE] Exclusão do ID {instance.entr_sequ} concluída")
            logger.info(f"✅ Exclusão concluída: ID {instance.entr_sequ}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"❌ Falha ao excluir entrada: {e}")
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @parametros_estoque_completo(operacao='entrada')
    def update(self, request, *args, **kwargs):
        from django.db import models
        from decimal import Decimal
        import re
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        db_alias = getattr(request, 'db_alias', get_licenca_db_config(request) or 'default')
        serializer = self.get_serializer(instance, data=self._merge_context_fields(request), partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic(using=db_alias):
                banco = db_alias
                empresa_id = getattr(request, 'empresa_id', None) or serializer.validated_data.get('entr_empr') or getattr(instance, 'entr_empr', 1)
                filial_id = getattr(request, 'filial_id', None) or serializer.validated_data.get('entr_fili') or getattr(instance, 'entr_fili', 1)
                old_lote = getattr(instance, 'entr_lote_vend', None)
                old_quan = Decimal(str(getattr(instance, 'entr_quan', 0) or 0))
                old_prod = str(getattr(instance, 'entr_prod', ''))
                instance = serializer.save()
                auto_lote = bool(request.data.get('auto_lote'))
                atualizar_preco = bool(request.data.get('atualizar_preco', True))
                lote_texto = (request.data.get('entr_lote_vend') or '').strip() if isinstance(request.data.get('entr_lote_vend'), str) else ''
                lote_label = lote_texto if (lote_texto and not lote_texto.isdigit()) else None
                if not getattr(instance, 'entr_lote_vend', None) and lote_texto and not re.search(r'\d', lote_texto):
                    from Produtos.models import Lote
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(instance.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    novo = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=instance.pk).update(entr_lote_vend=int(novo))
                    instance.entr_lote_vend = int(novo)
                elif auto_lote and not getattr(instance, 'entr_lote_vend', None):
                    from Produtos.models import Lote
                    ultimo = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(instance.entr_prod))
                        .aggregate(models.Max('lote_lote'))
                        .get('lote_lote__max')
                        or 0
                    )
                    novo = int(ultimo) + 1
                    EntradaEstoque.objects.using(banco).filter(pk=instance.pk).update(entr_lote_vend=int(novo))
                    instance.entr_lote_vend = int(novo)
                from Produtos.models import Lote
                new_lote = getattr(instance, 'entr_lote_vend', None)
                new_quan = Decimal(str(getattr(instance, 'entr_quan', 0) or 0))
                new_prod = str(getattr(instance, 'entr_prod', old_prod))
                lote_data_fabr = request.data.get('lote_data_fabr')
                lote_data_vali = request.data.get('lote_data_vali')
                try:
                    if lote_data_fabr and not hasattr(lote_data_fabr, 'year'):
                        from datetime import date
                        lote_data_fabr = date.fromisoformat(str(lote_data_fabr))
                except Exception:
                    lote_data_fabr = None
                try:
                    if lote_data_vali and not hasattr(lote_data_vali, 'year'):
                        from datetime import date
                        lote_data_vali = date.fromisoformat(str(lote_data_vali))
                except Exception:
                    lote_data_vali = None
                if old_lote and (old_lote != new_lote or old_prod != new_prod):
                    try:
                        lote_old = (
                            Lote.objects.using(banco)
                            .filter(lote_empr=int(empresa_id), lote_prod=str(old_prod), lote_lote=int(old_lote))
                            .first()
                        )
                        if lote_old:
                            saldo_atual = Decimal(str(getattr(lote_old, 'lote_sald', 0) or 0))
                            lote_old.lote_sald = (saldo_atual - old_quan).quantize(Decimal('0.01'))
                            lote_old.save(using=banco)
                    except Exception:
                        pass
                if new_lote:
                    lote = (
                        Lote.objects.using(banco)
                        .filter(lote_empr=int(empresa_id), lote_prod=str(new_prod), lote_lote=int(new_lote))
                        .first()
                    )
                    if not lote:
                        from decimal import Decimal as D
                        lote = Lote(
                            lote_empr=int(empresa_id),
                            lote_prod=str(new_prod),
                            lote_lote=int(new_lote),
                            lote_unit=D(str(getattr(instance, 'entr_unit', 0) or 0)),
                            lote_sald=D('0.00'),
                            lote_data_fabr=lote_data_fabr or getattr(instance, 'entr_data', None),
                            lote_data_vali=lote_data_vali,
                            lote_ativ=True,
                            lote_obse=lote_label,
                        )
                    elif lote_label and not getattr(lote, 'lote_obse', None):
                        lote.lote_obse = lote_label
                    if lote_data_fabr is not None:
                        lote.lote_data_fabr = lote_data_fabr
                    if lote_data_vali is not None:
                        lote.lote_data_vali = lote_data_vali
                    saldo_atual = Decimal(str(getattr(lote, 'lote_sald', 0) or 0))
                    delta = new_quan if (old_lote != new_lote or old_prod != new_prod) else (new_quan - old_quan)
                    lote.lote_sald = (saldo_atual + delta).quantize(Decimal('0.01'))
                    lote.save(using=banco)
                if atualizar_preco:
                    from Produtos.models import Tabelaprecos
                    update_fields = {
                        'tabe_cuge': Decimal(str(getattr(instance, 'entr_unit', 0) or 0)).quantize(Decimal('0.01')),
                        'tabe_entr': getattr(instance, 'entr_data', None),
                    }
                    preco_vista = request.data.get('preco_vista')
                    preco_prazo = request.data.get('preco_prazo')
                    if preco_vista is not None and str(preco_vista) != '':
                        update_fields['tabe_avis'] = Decimal(str(preco_vista)).quantize(Decimal('0.01'))
                    if preco_prazo is not None and str(preco_prazo) != '':
                        update_fields['tabe_apra'] = Decimal(str(preco_prazo)).quantize(Decimal('0.01'))
                    qs = Tabelaprecos.objects.using(banco).filter(
                        tabe_empr=int(empresa_id),
                        tabe_fili=int(filial_id),
                        tabe_prod=str(getattr(instance, 'entr_prod', new_prod)),
                    )
                    updated = qs.update(**update_fields)
                    if not updated:
                        create_fields = {
                            'tabe_empr': int(empresa_id),
                            'tabe_fili': int(filial_id),
                            'tabe_prod': str(getattr(instance, 'entr_prod', new_prod)),
                            **update_fields,
                        }
                        Tabelaprecos.objects.using(banco).create(**create_fields)
                out = self.get_serializer(instance)
                return Response(out.data, status=status.HTTP_200_OK)
        except IntegrityError as e:
            logger.error(f"IntegrityError: {e}")
            raise ValidationError({"detail": "Erro de integridade no banco de dados."})
