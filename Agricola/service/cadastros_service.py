import logging
from django.db import transaction
from django.db.models import Max
from django.core.exceptions import ValidationError
from ..models import (ProdutoAgro)
from Entidades.models import Entidades

logger = logging.getLogger(__name__)
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
        logger.info(f"Iniciando cadastrar_entidade. Empresa: {empresa}, Filial: {filial}, Dados: {dados.keys()}, Using: {using}")
        cadastros_unificados = ParametroAgricolaService.get(
            empresa, filial, "cadastros_unificados_entidades", using=using
        )
        logger.info(f"Cadastros unificados: {cadastros_unificados}")
        
        # Garante que enti_clie seja gerado se não existir
        if not dados.get("enti_clie"):
            ultimo_codigo = Entidades.objects.using(using).aggregate(Max("enti_clie"))["enti_clie__max"]
            dados["enti_clie"] = (ultimo_codigo or 0) + 1
            logger.info(f"Gerado novo enti_clie: {dados['enti_clie']}")


        # Remove campos que não pertencem ao model Entidades
        campos_validos = {f.name for f in Entidades._meta.get_fields()}
        dados_limpos = {k: v for k, v in dados.items() if k in campos_validos}
        
        # Garante criação/recuperação na empresa solicitada
        if not Entidades.objects.using(using).filter(enti_clie=dados["enti_clie"], enti_empr=empresa).exists():
            dados_origem = dados_limpos.copy()
            dados_origem["enti_empr"] = empresa
            logger.info(f"Criando entidade principal na empresa {empresa}")
            try:
                entidade_principal = Entidades.objects.using(using).create(**dados_origem)
                logger.info(f"Entidade principal criada com sucesso: {entidade_principal.pk}")
            except Exception as e:
                logger.error(f"Erro ao criar entidade principal: {e}")
                raise
        else:
            logger.info(f"Entidade já existe na empresa {empresa}, recuperando.")
            entidade_principal = Entidades.objects.using(using).get(enti_clie=dados["enti_clie"], enti_empr=empresa)

        if cadastros_unificados:
            # Obtém empresas distintas das filiais para replicação
            # Usando values para garantir consistência com cadastrar_produto
            todas_filiais = Filiais.objects.using(using).values('empr_empr').distinct()
            logger.info(f"Iniciando replicação para empresas (filiais distinct): {list(todas_filiais)}")
            
            for f in todas_filiais:
                empresa_dest = f['empr_empr']
                
                if empresa_dest == empresa:
                    continue

                # Verifica existência na empresa de destino
                exists = Entidades.objects.using(using).filter(
                    enti_clie=dados["enti_clie"],
                    enti_empr=empresa_dest
                ).exists()

                if not exists:
                    # Cria replica na empresa de destino
                    dados_replica = dados_limpos.copy()
                    dados_replica["enti_empr"] = empresa_dest
                    try:
                        logger.info(f"Replicando entidade para empresa {empresa_dest}")
                        Entidades.objects.using(using).create(**dados_replica)
                    except Exception as e:
                        logger.warning(f"Erro ao replicar para empresa {empresa_dest}: {e}")
                        pass # Ignora erro de duplicação na replicação
        
        return entidade_principal