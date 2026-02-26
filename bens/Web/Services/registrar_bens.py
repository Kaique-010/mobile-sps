from django.db import transaction
from decimal import Decimal

from django.views import static
from ...models import Bensptr, Grupobens, Motivosptr
from Agricola.service.sequencial_Service import SequencialService
from .depreciacao_service import DepreciacaoService

class MotivosService:
    @staticmethod
    @transaction.atomic
    def criar_motivo(*, dados, using):
        codigo = SequencialService.gerar(
            empresa=dados['moti_empr'],
            filial=dados['moti_fili'],
            tipo='MotivoBens',
            chave_extra=dados['moti_codi'],
            using=using,
        )
        dados['moti_codi'] = codigo
        descricao = dados['moti_desc'].upper()
        dados['moti_desc'] = descricao
        motivo = Motivosptr.objects.using(using).create(**dados)
        
        return motivo
    
    @staticmethod
    def update_motivo(*, motivo, validated_data, using):
        for key, value in validated_data.items():
            setattr(motivo, key, value)
        motivo.save(using=using)
        return motivo


    @staticmethod
    def get_motivo(*,codigo, using):
        try:
            return Motivosptr.objects.using(using).get(
               
                moti_codi=codigo,
            )
        except Motivosptr.DoesNotExist:
            return None

    @staticmethod
    def get_all(using):
        return Motivosptr.objects.using(using).all()

    @staticmethod
    def update(motivo, validated_data, using):
        for key, value in validated_data.items():
            setattr(motivo, key, value)
        motivo.save(using=using)
        return motivo

    @staticmethod
    def delete(motivo, using):
        motivo.delete(using=using)


class GrupobensService:
    @staticmethod
    @transaction.atomic
    def criar_grupo(*, dados, using):
        codigo = SequencialService.gerar(
            empresa=dados['grup_empr'],
            tipo='GrupoBens',
            chave_extra=dados['grup_codi'],
            using=using,
        )
        dados['grup_codi'] = codigo
        nome_grupo = dados['grup_nome'].upper()
        dados['grup_nome'] = nome_grupo
        vida_util = dados['grup_vida_util']
        dados['grup_vida_util'] = vida_util
        perc_depr_ano = dados['grup_perc_depr_ano']
        dados['grup_perc_depr_ano'] = perc_depr_ano
        perc_depr_mes = dados['grup_perc_depr_mes']
        dados['grup_perc_depr_mes'] = perc_depr_mes
        perc_depr_dia = dados['grup_perc_depr_dia']
        dados['grup_perc_depr_dia'] = perc_depr_dia
        
        grupo = Grupobens.objects.using(using).create(**dados)
        
        return grupo
    
    @staticmethod
    def get_all(using):
        return Grupobens.objects.using(using).all()
    
    @staticmethod
    def update_grupo(*, grupo, validated_data, using):
        for key, value in validated_data.items():
            setattr(grupo, key, value)
        grupo.save(using=using)
        return grupo

    @staticmethod
    def get_grupo(*,codigo, using):
        try:
            return Grupobens.objects.using(using).get(
               
                grup_codi=codigo,
            )
        except Grupobens.DoesNotExist:
            return None

    @staticmethod
    def delete(grupo, using):
        grupo.delete(using=using)


class BensptrService:
    @staticmethod
    @transaction.atomic
    def criar_bem(*, dados, using):
        # Mapeia chaves antigas se presentes para o padrão Bensptr
        if 'grup_codi' in dados and 'bens_grup' not in dados:
            dados['bens_grup'] = dados.pop('grup_codi')
        if 'moti_codi' in dados and 'bens_moti' not in dados:
            dados['bens_moti'] = dados.pop('moti_codi')

        # Busca grupo e preenche defaults
        grupo_id = dados.get('bens_grup')
        if grupo_id:
            grupo = GrupobensService.get_grupo(codigo=grupo_id, using=using)
            if grupo:
                # Se não informou vida útil, pega do grupo
                if not dados.get('bens_praz_vida'):
                    dados['bens_praz_vida'] = grupo.grup_vida_util
                
                # Se não informou taxas, pega do grupo
                if not dados.get('bens_depr_ano'):
                    dados['bens_depr_ano'] = grupo.grup_perc_depr_ano
                if not dados.get('bens_depr_mes'):
                    dados['bens_depr_mes'] = grupo.grup_perc_depr_mes
                if not dados.get('bens_depr_dia'):
                    dados['bens_depr_dia'] = grupo.grup_perc_depr_dia

        # Se ainda não tem taxas mas tem vida útil, calcula
        if dados.get('bens_praz_vida') and not dados.get('bens_depr_ano'):
             t_ano, t_mes, t_dia = DepreciacaoService.calcular_taxas_depreciacao(dados['bens_praz_vida'])
             dados['bens_depr_ano'] = t_ano
             dados['bens_depr_mes'] = t_mes
             dados['bens_depr_dia'] = t_dia
        
        codigo = SequencialService.gerar(
            empresa=dados['bens_empr'],
            filial=dados['bens_fili'],
            tipo='BensPatrimonio',
            chave_extra=None, 
            using=using,
        )
        dados['bens_codi'] = str(codigo)
        if dados.get('bens_desc'):
            dados['bens_desc'] = dados['bens_desc'].upper()
        
        # Limpeza de chaves extras se necessário, mas create(**dados) aceita apenas kwargs validos
        # Vamos assumir que dados venha limpo ou ignorar erros se vier chaves extras? 
        # Django create() lança TypeError se houver chaves inválidas.
        # Vamos remover chaves que sabemos que não existem no model se vierem de forms
        dados.pop('grup_codi', None)
        dados.pop('moti_codi', None)

        bem = Bensptr.objects.using(using).create(**dados)
        
        return bem

    @staticmethod
    def get_bem(*, empresa, filial, codigo, using):
        try:
            return Bensptr.objects.using(using).get(
                bens_empr=empresa,
                bens_fili=filial,
                bens_codi=codigo,
            )
        except Bensptr.DoesNotExist:
            return None

    @staticmethod
    def get_all(using):
        return Bensptr.objects.using(using).all()

    @staticmethod
    @transaction.atomic
    def update_bem(*, bem, validated_data, using):
        for key, value in validated_data.items():
            setattr(bem, key, value)
        bem.save(using=using)
        return bem

    @staticmethod
    @transaction.atomic
    def delete_bem(bem, using):
        bem.delete(using=using)

    @staticmethod
    @transaction.atomic
    def baixar_bem(*, bem, data_baixa, motivo, using):
        if not data_baixa:
            raise ValueError("Data de baixa é obrigatória para baixar o bem.")
        
        bem.bens_data_baix = data_baixa
        if motivo:
             bem.bens_moti = motivo
        
        bem.save(using=using)
        return bem
