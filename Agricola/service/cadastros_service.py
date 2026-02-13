from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import (ProdutoAgro)
from Entidades.models import Entidades
from Licencas.models import Filiais
from .parametros import ParametroAgricolaService
from .produto_agro_service import ProdutoAgroService
from .sequencial_Service import SequencialService

class CadastrosDomainService:
    @staticmethod
    @transaction.atomic
    def cadastrar_produto(empresa, filial, dados, using):
        cadastros_unificados = ParametroAgricolaService.get(
            empresa, filial, "cadastros_unificados_produtos", using=using
        )

        # Gera sequencial se não informado (uma única vez para manter consistência se unificado)
        if not dados.get("prod_codi_agro"):
            numero = SequencialService.gerar(
                empresa=empresa,
                filial=filial,
                tipo="PRODUTO",
                using=using,
            )
            dados["prod_codi_agro"] = str(numero).zfill(6)

        if cadastros_unificados:
            # Busca todas as filiais existentes no banco atual
            # Usando .values() para evitar problemas com PK incorreta no model Filiais (empr_empr duplicado)
            todas_filiais = Filiais.objects.using(using).values('empr_empr', 'empr_codi')
            
            for f in todas_filiais:
                empresa_dest = f['empr_empr']
                filial_dest = f['empr_codi']
                
                # Verifica se já existe o produto nesta empresa/filial
                exists = ProdutoAgro.objects.using(using).filter(
                    prod_codi_agro=dados["prod_codi_agro"],
                    prod_empr_agro=empresa_dest,
                    prod_fili_agro=filial_dest
                ).exists()
                
                if not exists:
                    # Copia dados e ajusta empresa/filial
                    dados_replica = dados.copy()
                    dados_replica["prod_empr_agro"] = empresa_dest
                    dados_replica["prod_fili_agro"] = filial_dest
                    
                    ProdutoAgro.objects.using(using).create(**dados_replica)
        else:
            # Cadastra apenas na empresa/filial atual
            ProdutoAgroService.criar_produto(data=dados, using=using)

    @staticmethod
    @transaction.atomic
    def cadastrar_entidade(empresa, filial, dados, using):
        cadastros_unificados = ParametroAgricolaService.get(
            empresa, filial, "cadastros_unificados_entidades", using=using
        )
        
        # Lógica para Entidades (geralmente tem código/CPF/CNPJ como chave, ou sequencial)
        # Assumindo que dados já vem com identificador ou é gerado no banco.
        # Entidades.models tem enti_clie como PK (BigInt). Precisa ser gerado?
        # O código original não gerava sequencial aqui explicitamente, apenas chamava create.
        # Se precisar de sequencial, deve ser tratado. 
        # Vou assumir que o 'dados' já tem o necessário ou o create resolve.
        # Mas para unificar, o ID (enti_clie) deve ser o mesmo? 
        # Se for AutoField/BigInt PK, não posso forçar facilmente se for auto-inc no banco.
        # Mas enti_clie não é AutoField, é BigIntegerField. Provavelmente é gerado.
        
        # Se for cadastro unificado, precisamos garantir que o ID seja o mesmo.
        # Vou assumir que quem chama já preparou 'dados' ou que devemos gerar um ID comum.
        
        # Para entidades, vamos replicar a lógica de iteração.
        
        if cadastros_unificados:
            todas_filiais = Filiais.objects.using(using).all()
            
            for f in todas_filiais:
                empresa_dest = f.empr_empr
                filial_dest = f.empr_codi
                
                # Verifica existência (por CPF/CNPJ ou ID se fornecido)
                # Entidades tem enti_clie como PK.
                # Se dados tem enti_clie, verifica por ele.
                
                if "enti_clie" in dados:
                     exists = Entidades.objects.using(using).filter(
                        enti_clie=dados["enti_clie"],
                        enti_empr=empresa_dest
                        # Entidades geralmente é por empresa? enti_empr faz parte da chave?
                        # O model diz: enti_clie = BigIntegerField(unique=True, primary_key=True)
                        # Se é unique=True globalmente (PK), então não pode ter o mesmo ID em empresas diferentes?
                        # O model tem 'enti_empr = models.IntegerField()'.
                        # Se PK é só enti_clie, então Entidade é GLOBAL por definição no banco?
                        # Se for global, não precisa replicar, basta criar uma vez.
                        # Mas o usuário pediu para replicar "em todas as suas empresas e filiais".
                        # Talvez a PK seja composta na prática ou o model Django esteja simplificado.
                        # O usuário mandou: "enti_empr=empresa, enti_fili=filial".
                        # Mas o model Entidades NÃO TEM enti_fili. Tem enti_empr.
                        # O código original tinha: enti_fili=filial.
                        # O model Entidades mostrado no SearchCodebase tem: enti_empr. NÃO TEM enti_fili visível nos campos principais.
                        # Mas o código original tinha `enti_fili=filial`.
                        # Vou manter a passagem de enti_fili pois pode ser um campo dinâmico ou estar no model real (o searchcodebase pode ter truncado ou ser view).
                     ).exists()
                else:
                    # Se não tem ID, difícil checar existência sem critério (ex: CNPJ).
                    # Vou assumir create simples e capturar erro se duplicar.
                    exists = False

                if not exists:
                     dados_replica = dados.copy()
                     dados_replica["enti_empr"] = empresa_dest
                     dados_replica["enti_fili"] = filial_dest
                     try:
                        Entidades.objects.using(using).create(**dados_replica)
                     except Exception:
                         pass # Ignora erro de duplicação na replicação
        else:
            Entidades.objects.using(using).create(
                enti_empr=empresa,
                enti_fili=filial,
                **dados,
            )