from decimal import Decimal, InvalidOperation
import logging
logger = logging.getLogger(__name__)
from django.db import transaction
from django.db.models import Max

from TrocasDevolucoes.models import TrocaDevolucao, ItensTrocaDevolucao


class TrocaDevolucaoService:
    @staticmethod
    def _to_decimal(value, default: str = '0'):
        try:
            if value is None:
                return Decimal(default)
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            s = str(value).strip().replace(',', '.')
            if s == '':
                return Decimal(default)
            return Decimal(s)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(default)

    @staticmethod
    def _to_int_or_none(value):
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            s = str(value).strip()
            if not s:
                return None
            digits = ''.join(ch for ch in s if ch.isdigit())
            if not digits:
                return None
            try:
                return int(digits)
            except Exception:
                return None

    @staticmethod
    def _normalizar_produto_codigo(value, max_len: int = 10) -> str:
        if value is None:
            return ''
        s = str(value).strip()
        if not s:
            return ''
        if s.isdigit():
            return s[:max_len]
        digits = ''.join(ch for ch in s if ch.isdigit())
        if digits:
            return digits[:max_len]
        return s[:max_len]

    @staticmethod
    def listar(banco, filtros=None):
        filtros = filtros or {}
        logger.debug(f"Listar TrocasDevolucoes banco={banco} filtros={filtros}")
        qs = TrocaDevolucao.objects.using(banco).all().order_by('-tdvl_nume')
        if filtros.get('tdvl_empr'):
            qs = qs.filter(tdvl_empr=filtros['tdvl_empr'])
        if filtros.get('tdvl_fili'):
            qs = qs.filter(tdvl_fili=filtros['tdvl_fili'])
        if filtros.get('tdvl_pdor'):
            qs = qs.filter(tdvl_pdor=filtros['tdvl_pdor'])
        if filtros.get('tdvl_stat'):
            qs = qs.filter(tdvl_stat=filtros['tdvl_stat'])
        return qs

    @staticmethod
    def _proximo_numero(banco, empresa, filial):
        ultimo = (
            TrocaDevolucao.objects.using(banco)
            .filter(tdvl_empr=empresa, tdvl_fili=filial)
            .aggregate(Max('tdvl_nume'))
            .get('tdvl_nume__max')
            or 0
        )
        proximo = int(ultimo) + 1
        logger.debug(f"_proximo_numero banco={banco} empresa={empresa} filial={filial} ultimo={ultimo} proximo={proximo}")
        return proximo


    @staticmethod
    def criar_com_itens(banco, dados, itens):
        numero = TrocaDevolucaoService._proximo_numero(banco, dados['tdvl_empr'], dados['tdvl_fili'])
        logger.info(f"Inicio criar_com_itens banco={banco} numero={numero} empr={dados.get('tdvl_empr')} fili={dados.get('tdvl_fili')} status={dados.get('tdvl_stat')} tipo={dados.get('tdvl_tipo')} itens={len(itens or [])}")
        with transaction.atomic(using=banco):
            tot_devo = Decimal('0.00')
            tot_repo = Decimal('0.00')
            for it in itens or []:
                tot_devo += Decimal(str(it.get('itdv_vlor') or 0))
                tot_repo += Decimal(str(it.get('itdv_vlre') or 0))
            dados.setdefault('tdvl_tode', tot_devo)
            dados.setdefault('tdvl_tore', tot_repo)
            dados.setdefault('tdvl_safi', (dados.get('tdvl_tode') or Decimal('0.00')) - (dados.get('tdvl_tore') or Decimal('0.00')))
            logger.debug(f"Totais calculados numero={numero} t_devo={dados['tdvl_tode']} t_repo={dados['tdvl_tore']} saldo={dados['tdvl_safi']}")

            troca = TrocaDevolucao.objects.using(banco).create(tdvl_nume=numero, **dados)
            logger.info(f"Troca criada numero={numero} id={getattr(troca, 'id', None)}")



            for idx, item in enumerate(itens or [], start=1):
                logger.debug(f"Criando item numero={numero} item={idx} pror={item.get('itdv_pror')} prre={item.get('itdv_prre')} qtor={item.get('itdv_qtor')} qtre={item.get('itdv_qtre')}")
                ItensTrocaDevolucao.objects.using(banco).create(
                    itdv_empr=dados['tdvl_empr'],
                    itdv_fili=dados['tdvl_fili'],
                    itdv_tdvl=numero,
                    itdv_item=idx,
                    **item,
                )

            if str(dados.get('tdvl_stat')) == '2':
                logger.info(f"Processando movimentacoes numero={numero} status=2")
                TrocaDevolucaoService._processar_movimentacoes(banco, troca)

            return troca

    @staticmethod
    def atualizar(banco, instance, dados, processar_movimentacoes=True):
        status_anterior = str(getattr(instance, 'tdvl_stat', '0') or '0')
        logger.info(f"Atualizar tdvl_nume={getattr(instance, 'tdvl_nume', None)} banco={banco} status_anterior={status_anterior} processar_mov={processar_movimentacoes}")
        logger.debug(f"Campos atualizados keys={list(dados.keys())}")
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        instance.save(using=banco)
        novo_status = str(getattr(instance, 'tdvl_stat', '0'))
        logger.debug(f"Atualizar salvo tdvl_nume={getattr(instance, 'tdvl_nume', None)} novo_status={novo_status}")
        if processar_movimentacoes and novo_status == '2' and status_anterior != '2':
            logger.info(f"Disparando movimentacoes tdvl_nume={getattr(instance, 'tdvl_nume', None)} status transicao {status_anterior}->2")
            TrocaDevolucaoService._processar_movimentacoes(banco, instance)
        return instance

    @staticmethod
    def concluir(banco, instance):
        logger.info(f"Concluir tdvl_nume={getattr(instance, 'tdvl_nume', None)} banco={banco}")
        TrocaDevolucaoService._processar_movimentacoes(banco, instance)

    @staticmethod
    def atualizar_itens(banco, instance, itens):
        with transaction.atomic(using=banco):
            qs = ItensTrocaDevolucao.objects.using(banco).filter(
                itdv_empr=instance.tdvl_empr,
                itdv_fili=instance.tdvl_fili,
                itdv_tdvl=instance.tdvl_nume,
            )
            del_count = qs.count()
            qs.delete()
            logger.info(f"Itens removidos tdvl_nume={instance.tdvl_nume} removidos={del_count}")
            for idx, item in enumerate(itens or [], start=1):
                logger.debug(f"Criando item atualizacao tdvl_nume={instance.tdvl_nume} item={idx} pror={item.get('itdv_pror')} prre={item.get('itdv_prre')}")
                ItensTrocaDevolucao.objects.using(banco).create(
                    itdv_empr=instance.tdvl_empr,
                    itdv_fili=instance.tdvl_fili,
                    itdv_tdvl=instance.tdvl_nume,
                    itdv_item=idx,
                    **item,
                )
            logger.info(f"Itens criados tdvl_nume={instance.tdvl_nume} total={len(itens or [])}")

    @staticmethod
    def _proximo_sequencial(using, model, field_name):
        ultimo = model.objects.using(using).aggregate(mx=Max(field_name)).get('mx') or 0
        try:
            proximo = int(ultimo) + 1
        except Exception:
            proximo = 1
        try:
            nome_model = getattr(model, '__name__', str(model))
        except Exception:
            nome_model = str(model)
        logger.debug(f"_proximo_sequencial using={using} model={nome_model} campo={field_name} ultimo={ultimo} proximo={proximo}")
        return proximo

    @staticmethod
    def _processar_movimentacoes(banco, instance):
        from Saidas_Estoque.models import SaidasEstoque
        from Entradas_Estoque.models import EntradaEstoque
        from adiantamentos.services import AdiantamentosService

        itens = ItensTrocaDevolucao.objects.using(banco).filter(
            itdv_empr=instance.tdvl_empr,
            itdv_fili=instance.tdvl_fili,
            itdv_tdvl=instance.tdvl_nume,
        )

        with transaction.atomic(using=banco):
            logger.info(f"Iniciando processamento de movimentacoes banco={banco} tdvl_nume={instance.tdvl_nume} tipo={instance.tdvl_tipo}")
            logger.debug(f"Quantidade de itens para movimentacao tdvl_nume={instance.tdvl_nume}: {itens.count()}")
            proximo_saida = TrocaDevolucaoService._proximo_sequencial(banco, SaidasEstoque, 'said_sequ')
            logger.info(f"Proximo_saida={proximo_saida}")
            proximo_entrada = TrocaDevolucaoService._proximo_sequencial(banco, EntradaEstoque, 'entr_sequ')
            obs_base = f"{'Troca' if str(instance.tdvl_tipo) == 'TROC' else 'Devolução'} {instance.tdvl_nume} - Pedido {instance.tdvl_pdor}"
            logger.info(f"Proximo_entrada={proximo_entrada}")

            ent_enti = str(instance.tdvl_clie or '').strip()[:10] or None

            entradas_antigas = EntradaEstoque.objects.using(banco).filter(
                entr_empr=instance.tdvl_empr,
                entr_fili=instance.tdvl_fili,
                entr_obse=obs_base,
            )
            saidas_antigas = SaidasEstoque.objects.using(banco).filter(
                said_empr=instance.tdvl_empr,
                said_fili=instance.tdvl_fili,
                said_obse=obs_base,
            )
            entradas_removidas = entradas_antigas.count()
            saidas_removidas = saidas_antigas.count()
            if entradas_removidas:
                entradas_antigas.delete()
            if saidas_removidas:
                saidas_antigas.delete()
            if entradas_removidas or saidas_removidas:
                logger.info(f"Movimentacoes anteriores removidas tdvl_nume={instance.tdvl_nume} entradas={entradas_removidas} saidas={saidas_removidas}")

            for it in itens:
                qtd_origem = TrocaDevolucaoService._to_decimal(getattr(it, 'itdv_qtor', 0) or 0, default='0')
                val_origem = TrocaDevolucaoService._to_decimal(getattr(it, 'itdv_vlor', 0) or 0, default='0')
                prod_origem = TrocaDevolucaoService._normalizar_produto_codigo(getattr(it, 'itdv_pror', '') or '')
                if qtd_origem and prod_origem:
                    logger.debug(f"Entrada estoque tdvl={instance.tdvl_nume} sequ={proximo_entrada} prod={prod_origem} qtd={qtd_origem} val={val_origem}")
                    EntradaEstoque.objects.using(banco).create(
                        entr_empr=instance.tdvl_empr,
                        entr_fili=instance.tdvl_fili,
                        entr_sequ=proximo_entrada,
                        entr_data=instance.tdvl_data,
                        entr_prod=prod_origem,
                        entr_quan=qtd_origem,
                        entr_tota=val_origem,
                        entr_obse=obs_base,
                        entr_usua=1,
                        entr_enti=ent_enti,
                    )
                    proximo_entrada += 1

                if str(instance.tdvl_tipo) == 'TROC':
                    prod_repo = TrocaDevolucaoService._normalizar_produto_codigo(getattr(it, 'itdv_prre', '') or '')
                    qtd_repo = TrocaDevolucaoService._to_decimal(getattr(it, 'itdv_qtre', 0) or 0, default='0')
                    val_repo = TrocaDevolucaoService._to_decimal(getattr(it, 'itdv_vlre', 0) or 0, default='0')
                    if prod_repo and qtd_repo:
                        logger.debug(f"Saida estoque tdvl={instance.tdvl_nume} sequ={proximo_saida} prod={prod_repo} qtd={qtd_repo} val={val_repo}")
                        SaidasEstoque.objects.using(banco).create(
                            said_empr=instance.tdvl_empr,
                            said_fili=instance.tdvl_fili,
                            said_sequ=proximo_saida,
                            said_data=instance.tdvl_data,
                            said_prod=prod_repo,
                            said_quan=qtd_repo,
                            said_tota=val_repo,
                            said_obse=obs_base,
                            said_usua=1,
                            said_enti=ent_enti,
                        )
                        proximo_saida += 1
            try:
                valor_saldo = TrocaDevolucaoService._to_decimal(getattr(instance, 'tdvl_safi', 0) or 0, default='0')
                if valor_saldo > 0:
                    adia_enti = TrocaDevolucaoService._to_int_or_none(getattr(instance, 'tdvl_clie', None))
                    adia_docu = TrocaDevolucaoService._to_int_or_none(getattr(instance, 'tdvl_nume', None))
                    if adia_enti is None or adia_docu is None:
                        logger.warning(f"Adiantamento ignorado tdvl_nume={getattr(instance, 'tdvl_nume', None)} clie={getattr(instance, 'tdvl_clie', None)}: entidade/docu inválidos")
                    else:
                        logger.info(f"Criando adiantamento tdvl_nume={instance.tdvl_nume} valor={valor_saldo} enti={adia_enti} seri=TDV tipo=R")
                        dados = {
                            'adia_empr': instance.tdvl_empr,
                            'adia_fili': instance.tdvl_fili,
                            'adia_enti': adia_enti,
                            'adia_docu': adia_docu,
                            'adia_seri': 'TDV',
                            'adia_tipo': 'R',
                            'adia_valo': valor_saldo,
                            'adia_sald': valor_saldo,
                            'adia_obse': obs_base,
                        }
                        existente = AdiantamentosService.get_adiantamento(
                            empresa=instance.tdvl_empr,
                            entidade=adia_enti,
                            documento=adia_docu,
                            serie='TDV',
                            using=banco,
                        )
                        if existente:
                            AdiantamentosService.update(
                                existente,
                                {'adia_tipo': 'R', 'adia_valo': valor_saldo, 'adia_sald': valor_saldo, 'adia_obse': obs_base},
                                using=banco,
                            )
                        else:
                            AdiantamentosService.criar_adiantamento(dados=dados, using=banco)
            except Exception as e:
                logger.exception(f"Falha ao criar adiantamento tdvl_nume={getattr(instance, 'tdvl_nume', None)}: {e}")
                pass
