from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.db.models import Max
from ..models import EntradaEstoque
from Produtos.models import Produtos
from Licencas.models import Empresas
from core.serializers import BancoContextMixin
import logging

logger = logging.getLogger(__name__)

class EntradasEstoqueSerializer(BancoContextMixin, serializers.ModelSerializer):
    empresa_nome = serializers.SerializerMethodField()
    produto_nome = serializers.SerializerMethodField()
    entidade_nome = serializers.SerializerMethodField()
    lote_data_fabr = serializers.SerializerMethodField()
    lote_data_vali = serializers.SerializerMethodField()
    preco_vista = serializers.SerializerMethodField()
    preco_prazo = serializers.SerializerMethodField()
    auto_lote = serializers.BooleanField(read_only=True, default=False)
    atualizar_preco = serializers.BooleanField(read_only=True, default=True)

    class Meta:
        model = EntradaEstoque
        fields = '__all__'
        extra_kwargs = {
            'entr_sequ': {'read_only': True}
        }

    def get_produto_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            # Verificar se a data é válida antes de fazer a query
            if hasattr(obj, 'entr_data') and obj.entr_data:
                try:
                    # Tentar acessar o ano da data para verificar se é válida
                    year = obj.entr_data.year
                    if year < 1900:
                        logger.warning(f"Data inválida no registro {obj.entr_sequ}: {obj.entr_data}")
                        return "Produto com data inválida"
                except (ValueError, AttributeError) as date_error:
                    logger.warning(f"Erro na data do registro {obj.entr_sequ}: {date_error}")
                    return "Produto com data inválida"
            
            produto = Produtos.objects.using(banco).filter(
                prod_codi=obj.entr_prod,
                prod_empr=obj.entr_empr
            ).first()
            return produto.prod_nome if produto else None
        except Produtos.DoesNotExist:
            logger.warning(f"Produto com ID {obj.entr_prod} não encontrado.")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar produto para entrada {obj.entr_sequ}: {e}")
            return None

    def get_empresa_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            empresa = Empresas.objects.using(banco).filter(
                empr_codi=obj.entr_empr
            ).first()
            return empresa.empr_nome if empresa else None
        except Exception as e:
            logger.error(f"Erro ao buscar empresa: {e}")
            return None
    
    def get_entidade_nome(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            from Entidades.models import Entidades
            entidade_nome = Entidades.objects.using(banco).filter(
                enti_clie=obj.entr_enti
            ).first()
            print(entidade_nome)
            return entidade_nome.enti_nome if entidade_nome else None
        except Exception as e:
            logger.error(f"Erro ao buscar entidade: {e}")
            return None

    def _get_lote_obj(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        lote_num = getattr(obj, 'entr_lote_vend', None)
        if not lote_num:
            return None
        try:
            from Produtos.models import Lote
            prod_variants = self._prod_variants(getattr(obj, 'entr_prod', None))
            key = (int(obj.entr_empr), tuple(prod_variants), int(lote_num))
            cache = getattr(self, '_lote_cache', None)
            if cache is None:
                cache = {}
                setattr(self, '_lote_cache', cache)
            if key in cache:
                return cache[key]
            lote = (
                Lote.objects.using(banco)
                .filter(
                    lote_empr=int(obj.entr_empr),
                    lote_prod__in=prod_variants,
                    lote_lote=int(lote_num),
                )
                .first()
            )
            cache[key] = lote
            return lote
        except Exception:
            return None

    def get_lote_data_fabr(self, obj):
        lote = self._get_lote_obj(obj)
        data = getattr(lote, 'lote_data_fabr', None) if lote else None
        return data.isoformat() if hasattr(data, 'isoformat') else data

    def get_lote_data_vali(self, obj):
        lote = self._get_lote_obj(obj)
        data = getattr(lote, 'lote_data_vali', None) if lote else None
        return data.isoformat() if hasattr(data, 'isoformat') else data

    def _get_preco_obj(self, obj):
        banco = self.context.get('banco')
        if not banco:
            return None
        try:
            from Produtos.models import Tabelaprecos
            prod_variants = self._prod_variants(getattr(obj, 'entr_prod', None))
            key = (int(obj.entr_empr), int(obj.entr_fili), tuple(prod_variants))
            cache = getattr(self, '_preco_cache', None)
            if cache is None:
                cache = {}
                setattr(self, '_preco_cache', cache)
            if key in cache:
                return cache[key]
            preco = (
                Tabelaprecos.objects.using(banco)
                .filter(
                    tabe_empr=int(obj.entr_empr),
                    tabe_fili=int(obj.entr_fili),
                    tabe_prod__in=prod_variants,
                )
                .first()
            )
            cache[key] = preco
            return preco
        except Exception:
            return None

    def get_preco_vista(self, obj):
        preco = self._get_preco_obj(obj)
        val = getattr(preco, 'tabe_avis', None) if preco else None
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    def get_preco_prazo(self, obj):
        preco = self._get_preco_obj(obj)
        val = getattr(preco, 'tabe_apra', None) if preco else None
        try:
            return float(val) if val is not None else None
        except Exception:
            return None

    def _prod_variants(self, value):
        if value is None:
            return ['']
        s = str(value).strip()
        variants = []
        if s:
            variants.append(s)
            if s.isdigit():
                variants.append(s.zfill(6))
                variants.append(str(int(s)))
        seen = set()
        out = []
        for v in variants:
            if v and v not in seen:
                out.append(v)
                seen.add(v)
        return out or ['']

    def create(self, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não especificado no contexto")
        
        # Gerar próximo número sequencial
        max_sequ = EntradaEstoque.objects.using(banco).aggregate(
            max_sequ=Max('entr_sequ')
        )['max_sequ'] or 0
        validated_data['entr_sequ'] = max_sequ + 1
        
        return EntradaEstoque.objects.using(banco).create(**validated_data)

    def update(self, instance, validated_data):
        banco = self.context.get('banco')
        if not banco:
            raise ValidationError("Banco não especificado no contexto")
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance
