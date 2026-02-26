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
        codigo = Motivosptr.objects.using(using).count() + 1
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
        print(f"DEBUG: criar_grupo called with dados: {dados}")
        # Garante que chave_extra seja None se não vier no dados
        chave_extra = dados.get('grup_codi')
        
        codigo = SequencialService.gerar(
            empresa=dados['grup_empr'],
            filial=1, 
            tipo='GrupoBens',
            chave_extra=chave_extra,
            using=using,
        )
        dados['grup_codi'] = codigo
        
        if dados.get('grup_nome'):
            dados['grup_nome'] = dados['grup_nome'].upper()
            
        # Calcular taxas se necessário
        vida_util = dados.get('grup_vida_util')
        perc_depr_ano = dados.get('grup_perc_depr_ano')
        
        if vida_util and not perc_depr_ano:
             t_ano, t_mes, t_dia = DepreciacaoService.calcular_taxas_depreciacao(vida_util)
             dados['grup_perc_depr_ano'] = t_ano
             dados['grup_perc_depr_mes'] = t_mes
             dados['grup_perc_depr_dia'] = t_dia
        elif perc_depr_ano:
             # Se tem a taxa anual, deriva as outras
             dados['grup_perc_depr_mes'] = perc_depr_ano / Decimal('12')
             dados['grup_perc_depr_dia'] = perc_depr_ano / Decimal('365')
        else:
             # Garante valores zerados se nada foi informado
             dados.setdefault('grup_perc_depr_mes', Decimal('0'))
             dados.setdefault('grup_perc_depr_dia', Decimal('0'))
             dados.setdefault('grup_perc_depr_ano', Decimal('0'))
        
        grupo = Grupobens.objects.using(using).create(**dados)
        
        return grupo
    
    @staticmethod
    def get_all(using):
        return Grupobens.objects.using(using).all()
    
    @staticmethod
    def update_grupo(*, grupo, validated_data, using):
        vida_util = validated_data.get('grup_vida_util')
        perc_depr_ano = validated_data.get('grup_perc_depr_ano')
        
        # Se vida util veio mas taxa não (ex: campo limpo), tenta calcular
        if vida_util and not perc_depr_ano:
             t_ano, t_mes, t_dia = DepreciacaoService.calcular_taxas_depreciacao(vida_util)
             validated_data['grup_perc_depr_ano'] = t_ano
             validated_data['grup_perc_depr_mes'] = t_mes
             validated_data['grup_perc_depr_dia'] = t_dia
        
        # Se tem taxa anual (vinda do form ou calculada acima), atualiza as derivadas
        if validated_data.get('grup_perc_depr_ano'):
             p_ano = validated_data['grup_perc_depr_ano']
             validated_data['grup_perc_depr_mes'] = p_ano / Decimal('12')
             validated_data['grup_perc_depr_dia'] = p_ano / Decimal('365')

        for key, value in validated_data.items():
            setattr(grupo, key, value)
        grupo.save(using=using)
        return grupo

    @staticmethod
    def get_grupo(*, codigo, empresa=None, using):
        try:
            if empresa:
                return Grupobens.objects.using(using).get(grup_codi=codigo, grup_empr=empresa)
            return Grupobens.objects.using(using).get(grup_codi=codigo)
        except Grupobens.DoesNotExist:
            return None
        except Grupobens.MultipleObjectsReturned:
            # Fallback: pega o primeiro
             if empresa:
                return Grupobens.objects.using(using).filter(grup_codi=codigo, grup_empr=empresa).first()
             return Grupobens.objects.using(using).filter(grup_codi=codigo).first()

    @staticmethod
    def delete(grupo, using):
        grupo.delete(using=using)


class BensptrService:
    @staticmethod
    @transaction.atomic
    def criar_bem(*, dados, using):
        print(f"DEBUG: criar_bem called with dados: {dados}")
        # Mapeia chaves antigas se presentes para o padrão Bensptr
        if 'grup_codi' in dados and 'bens_grup' not in dados:
            dados['bens_grup'] = dados.pop('grup_codi')
        if 'moti_codi' in dados and 'bens_moti' not in dados:
            dados['bens_moti'] = dados.pop('moti_codi')

        # Busca grupo e preenche defaults
        grupo_id = dados.get('bens_grup')
        empresa = dados.get('bens_empr')
        
        if grupo_id:
            grupo = GrupobensService.get_grupo(codigo=grupo_id, empresa=empresa, using=using)
            if grupo:
                print(f"DEBUG: Found grupo: {grupo}")
                # Se não informou vida útil, pega do grupo
                if not dados.get('bens_praz_vida'):
                    dados['bens_praz_vida'] = grupo.grup_vida_util
                
                # Se não informou taxas, pega do grupo
                # O model Bensptr usa bens_depr_ano (não grup_perc_depr_ano)
                # Vamos checar se precisamos preencher outros campos de taxa no Bensptr?
                # Model Bensptr tem bens_depr_ano. Tem bens_depr_mes? Não vi no dump.
                # Assumindo que só tem bens_depr_ano por enquanto.
                
                if not dados.get('bens_depr_ano'):
                    dados['bens_depr_ano'] = grupo.grup_perc_depr_ano
            else:
                 print(f"DEBUG: Grupo not found for id {grupo_id} and empresa {empresa}")

        # Se ainda não tem taxas mas tem vida útil, calcula
        if dados.get('bens_praz_vida') and not dados.get('bens_depr_ano'):
             t_ano, t_mes, t_dia = DepreciacaoService.calcular_taxas_depreciacao(dados['bens_praz_vida'])
             dados['bens_depr_ano'] = t_ano
             # Se Bensptr tiver campos de mes/dia, adicionamos aqui. Se não, ignoramos.
             
        # Limpar campos que não existem no model Bensptr antes de criar
        # O create(**dados) vai falhar se tiver campos extras.
        # Vamos listar campos válidos do model ou usar apenas os que conhecemos?
        # Ou filtrar dados.
        
        # Vamos filtrar dados com base nos campos do model
        valid_fields = [f.name for f in Bensptr._meta.get_fields()]
        dados_filtrados = {k: v for k, v in dados.items() if k in valid_fields}
        
        print(f"DEBUG: dados_filtrados: {dados_filtrados}")
        
        codigo = SequencialService.gerar(
            empresa=dados['bens_empr'],
            filial=dados['bens_fili'],
            tipo='Bensptr',
            using=using,
        )
        dados_filtrados['bens_codi'] = str(codigo)
        dados_filtrados['bens_empr'] = dados['bens_empr']
        dados_filtrados['bens_fili'] = dados['bens_fili']
        
        if dados.get('bens_desc'):
            dados_filtrados['bens_desc'] = dados['bens_desc'].upper()
        
        # Garante que campos obrigatórios estejam presentes ou trata None
        # bens_desc é obrigatório? Sim, mas o form deve garantir.
        # bens_grup é IntegerField.
        
        bem = Bensptr.objects.using(using).create(**dados_filtrados)
        
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
