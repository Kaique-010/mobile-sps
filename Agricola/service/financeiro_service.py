from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from ..models import  MovimentacaoEstoque
from contas_a_receber.models import Titulosreceber
from contas_a_pagar.models import Titulospagar
from .parametros import ParametroAgricolaService
import logging

logger = logging.getLogger(__name__)

class AgricolaFinanceiroService:
    @staticmethod
    def gerar_titulo_movimentacao(movimentacao, using='default', force=False):
        logger.info(f"[AgricolaFinanceiroService] Iniciando geração. ID: {movimentacao.id}, Tipo: {movimentacao.movi_estq_tipo}, Force: {force}")
        
        # Verifica se o parâmetro está ativo
        gera_financeiro = ParametroAgricolaService.get(
            movimentacao.movi_estq_empr, 
            movimentacao.movi_estq_fili, 
            "movimentacao_gera_financeiro",
            using=using
        )
        logger.info(f"[AgricolaFinanceiroService] Parâmetro 'movimentacao_gera_financeiro': {gera_financeiro}")
        
        if not gera_financeiro and not force:
            logger.info("[AgricolaFinanceiroService] Geração desativada por parâmetro.")
            return None

        # Verifica dados mínimos
        if not movimentacao.movi_estq_enti or not movimentacao.movi_estq_cust_tota:
            logger.warning(f"[AgricolaFinanceiroService] Dados insuficientes: Entidade={movimentacao.movi_estq_enti}, CustoTotal={movimentacao.movi_estq_cust_tota}")
            return None
            
        vencimento = movimentacao.movi_estq_venc or movimentacao.movi_estq_data.date()
        forma_pagamento = movimentacao.movi_estq_form_paga or "54" # Default Dinheiro/Outros
        
        # Mapeamento do documento
        documento = movimentacao.movi_estq_docu_refe or f"MOV{movimentacao.id}"
        documento = str(documento).strip()
        if not documento:
             documento = f"MOV{movimentacao.id}"

        # Truncate doc number to 13 chars
        documento_trunc = documento[:13]
        
        created_title = None
        
        try:
            # Não usa transaction.atomic aqui porque já deve estar dentro de uma transação no save()
            # ou deve ser gerenciado por quem chama
            if movimentacao.movi_estq_tipo == 'entrada':
                # Gera Conta a Pagar
                # Verifica duplicidade simples
                exists = Titulospagar.objects.using(using).filter(
                    titu_empr=movimentacao.movi_estq_empr,
                    titu_fili=movimentacao.movi_estq_fili,
                    titu_forn=movimentacao.movi_estq_enti,
                    titu_titu=documento_trunc,
                    titu_seri="MOV",
                    titu_parc="1"
                ).exists()
                

                if not exists:
                    logger.info(f"[AgricolaFinanceiroService] Criando Titulospagar para Fornecedor {movimentacao.movi_estq_enti}")
                    created_title = Titulospagar.objects.using(using).create(
                        titu_empr=movimentacao.movi_estq_empr,
                        titu_fili=movimentacao.movi_estq_fili,
                        titu_forn=movimentacao.movi_estq_enti,
                        titu_titu=documento_trunc,
                        titu_seri="MOV",
                        titu_parc="1",
                        titu_emis=movimentacao.movi_estq_data.date(),
                        titu_venc=vencimento,
                        titu_valo=movimentacao.movi_estq_cust_tota,
                        titu_hist=f"Ref. Movimentação Estoque {movimentacao.id} - {movimentacao.movi_estq_moti or ''}",
                        titu_form_reci=forma_pagamento,
                        titu_situ=1, # Aberto?
                        titu_aber='A',
                        titu_tipo="Pagar",
                        titu_prov=True
                    )
                else:
                    logger.info("[AgricolaFinanceiroService] Titulospagar já existe.")

            elif movimentacao.movi_estq_tipo == 'saida':
                # Gera Conta a Receber
                exists = Titulosreceber.objects.using(using).filter(
                    titu_empr=movimentacao.movi_estq_empr,
                    titu_fili=movimentacao.movi_estq_fili,
                    titu_clie=movimentacao.movi_estq_enti,
                    titu_titu=documento_trunc,
                    titu_seri="MOV",
                    titu_parc="1"
                ).exists()
                
                if not exists:
                    logger.info(f"[AgricolaFinanceiroService] Criando Titulosreceber para Cliente {movimentacao.movi_estq_enti}")
                    created_title = Titulosreceber.objects.using(using).create(
                        titu_empr=movimentacao.movi_estq_empr,
                        titu_fili=movimentacao.movi_estq_fili,
                        titu_clie=movimentacao.movi_estq_enti,
                        titu_titu=documento_trunc,
                        titu_seri="MOV",
                        titu_parc="1",
                        titu_emis=movimentacao.movi_estq_data.date(),
                        titu_venc=vencimento,
                        titu_valo=movimentacao.movi_estq_cust_tota,
                        titu_hist=f"Ref. Movimentação Estoque {movimentacao.id} - {movimentacao.movi_estq_moti or ''}",
                        titu_form_reci=forma_pagamento,
                        titu_situ=1,
                        titu_aber='A',
                        titu_tipo="Receber",
                        titu_prov=True
                    )
                else:
                    logger.info("[AgricolaFinanceiroService] Titulosreceber já existe.")
                    
        except Exception as e:
            logger.error(f"[AgricolaFinanceiroService] Erro ao criar título: {e}", exc_info=True)
            raise e
            
        return created_title
