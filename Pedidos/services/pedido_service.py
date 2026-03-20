from django.db import transaction
import logging
from decimal import Decimal, InvalidOperation
from django.db.models import Max
from ..models import PedidoVenda, Itenspedidovenda
from Produtos.models import SaldoProduto
from CFOP.services.services import MotorFiscal
from core.utils import (
    calcular_subtotal_item_bruto,
    calcular_total_item_com_desconto,
)
from CFOP.services.bases import FiscalContexto
from parametros_admin.utils_pedidos import verificar_baixa_estoque_pedido
class PedidoVendaService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _to_decimal(value, default: str = '0.00') -> Decimal:
        """Converte valores diversos para Decimal de forma robusta.
        Trata None, string vazia e vírgula decimal. Em caso de falha, retorna default.
        """
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
        except (InvalidOperation, ValueError, TypeError) as e:
            PedidoVendaService.logger.warning("[_to_decimal] valor inválido=%r, fallback=%s, err=%s", value, default, e)
            return Decimal(default)

    @staticmethod
    def _normalizar_codigo_produto(banco: str, pedido, produto_codigo) -> str:
        from Produtos.models import Produtos

        if produto_codigo is None:
            return ''

        codigo = str(produto_codigo).strip()
        if not codigo:
            return ''

        prod = Produtos.objects.using(banco).filter(
            prod_empr=str(pedido.pedi_empr),
            prod_codi=codigo,
        ).first()
        if prod:
            return str(prod.prod_codi)

        if codigo.isdigit():
            prod = Produtos.objects.using(banco).filter(
                prod_empr=str(pedido.pedi_empr),
                prod_codi_nume=codigo,
            ).first()
            if prod:
                return str(prod.prod_codi)

        return codigo

    @staticmethod
    def pedido_tem_baixa(banco: str, pedido) -> bool:
        from Saidas_Estoque.models import SaidasEstoque

        return SaidasEstoque.objects.using(banco).filter(
            said_empr=pedido.pedi_empr,
            said_fili=pedido.pedi_fili,
            said_obse__exact=f"Saída automática - Pedido {pedido.pedi_nume}",
        ).exists()

    @staticmethod
    def pedido_tem_estorno(banco: str, pedido) -> bool:
        from Saidas_Estoque.models import SaidasEstoque

        base = f"Saída automática - Pedido {pedido.pedi_nume}"
        return SaidasEstoque.objects.using(banco).filter(
            said_empr=pedido.pedi_empr,
            said_fili=pedido.pedi_fili,
            said_obse__startswith=base,
            said_obse__icontains="REVERTIDA",
        ).exists()

    @staticmethod
    def _baixar_item_data(pedido, item_data: dict, banco: str, request=None) -> dict:
        from Saidas_Estoque.models import SaidasEstoque
        from parametros_admin.utils_estoque import verificar_estoque_negativo

        produto_codigo = PedidoVendaService._normalizar_codigo_produto(banco, pedido, item_data.get('iped_prod'))
        quantidade = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0), default='0.00')
        valor_unitario = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0), default='0.00')
        valor_total = item_data.get('iped_tota')

        if quantidade <= 0:
            return {'sucesso': True, 'processado': False, 'motivo': 'Quantidade inválida'}

        base_obse = f"Saída automática - Pedido {pedido.pedi_nume}"
        ja_baixado = SaidasEstoque.objects.using(banco).filter(
            said_empr=pedido.pedi_empr,
            said_fili=pedido.pedi_fili,
            said_prod=str(produto_codigo),
            said_obse__exact=base_obse,
        ).exists()
        if ja_baixado:
            return {'sucesso': True, 'processado': False, 'motivo': 'Item já baixado para este pedido'}

        saldo = SaldoProduto.objects.using(banco).filter(
            produto_codigo=produto_codigo,
            empresa=str(pedido.pedi_empr),
            filial=str(pedido.pedi_fili),
        ).first()

        if saldo and saldo.saldo_estoque < abs(quantidade):
            permite_negativo = False
            if request is not None:
                try:
                    permite_negativo = verificar_estoque_negativo(pedido.pedi_empr, pedido.pedi_fili, request)
                except Exception:
                    permite_negativo = False
            if not permite_negativo:
                return {'sucesso': False, 'erro': f"Produto {produto_codigo} sem estoque suficiente"}

        ultimo = SaidasEstoque.objects.using(banco).aggregate(mx=Max('said_sequ')).get('mx')
        proximo_sequencial = (int(ultimo) + 1) if ultimo else 1

        if valor_total is not None:
            total_movimentacao = PedidoVendaService._to_decimal(valor_total, default='0.00').quantize(Decimal('0.01'))
        else:
            total_movimentacao = (valor_unitario * abs(quantidade)).quantize(Decimal('0.01'))
        usuario_id = getattr(getattr(request, 'user', None), 'usua_codi', 1) if request is not None else 1
        SaidasEstoque.objects.using(banco).create(
            said_empr=pedido.pedi_empr,
            said_fili=pedido.pedi_fili,
            said_sequ=proximo_sequencial,
            said_data=pedido.pedi_data,
            said_prod=str(produto_codigo),
            said_quan=abs(quantidade),
            said_tota=total_movimentacao,
            said_obse=base_obse,
            said_usua=usuario_id,
            said_enti=str(pedido.pedi_forn),
        )

        saldo, _ = SaldoProduto.objects.using(banco).get_or_create(
            produto_codigo=produto_codigo,
            empresa=str(pedido.pedi_empr),
            filial=str(pedido.pedi_fili),
            defaults={'saldo_estoque': Decimal('0.00')},
        )
        saldo.saldo_estoque -= abs(quantidade)
        saldo.save(using=banco, update_fields=["saldo_estoque"])

        return {'sucesso': True, 'processado': True}

    @staticmethod
    def _estornar_item(pedido, item, banco: str) -> dict:
        try:
            from Saidas_Estoque.models import SaidasEstoque

            produto_codigo = str(getattr(item, 'iped_prod', '') or '')
            if not produto_codigo:
                return {'sucesso': True, 'processado': False, 'motivo': 'Produto inválido'}

            base_obse = f"Saída automática - Pedido {pedido.pedi_nume}"
            saidas = SaidasEstoque.objects.using(banco).filter(
                said_empr=pedido.pedi_empr,
                said_fili=pedido.pedi_fili,
                said_prod=produto_codigo,
                said_obse__exact=base_obse,
            )
            if not saidas.exists():
                return {'sucesso': True, 'processado': False, 'motivo': 'Item sem baixa para estornar'}

            processado = False
            for saida in saidas:
                saldo, _ = SaldoProduto.objects.using(banco).get_or_create(
                    produto_codigo=produto_codigo,
                    empresa=str(pedido.pedi_empr),
                    filial=str(pedido.pedi_fili),
                    defaults={'saldo_estoque': Decimal('0.00')},
                )
                saldo.saldo_estoque += Decimal(str(saida.said_quan or 0))
                saldo.save(using=banco, update_fields=["saldo_estoque"])

                saida.said_obse = f"{base_obse} - REVERTIDA"
                saida.save(using=banco, update_fields=["said_obse"])
                processado = True

            return {'sucesso': True, 'processado': processado}
        except Exception as e:
            return {'sucesso': False, 'erro': f"Erro ao estornar item {getattr(item, 'iped_prod', None)}: {str(e)}"}

    @staticmethod
    @transaction.atomic
    def estornar_estoque_pedido(pedido, banco: str) -> dict:
        from Saidas_Estoque.models import SaidasEstoque

        base_obse = f"Saída automática - Pedido {pedido.pedi_nume}"
        saidas = SaidasEstoque.objects.using(banco).filter(
            said_empr=pedido.pedi_empr,
            said_fili=pedido.pedi_fili,
            said_obse__startswith=base_obse,
        ).exclude(said_obse__icontains="REVERTIDA")

        if not saidas.exists():
            return {'sucesso': True, 'processado': False, 'motivo': 'Pedido sem baixa de estoque para estornar'}

        processado = False
        for saida in saidas:
            produto_codigo = PedidoVendaService._normalizar_codigo_produto(banco, pedido, getattr(saida, 'said_prod', ''))
            if not produto_codigo:
                continue

            saldo, _ = SaldoProduto.objects.using(banco).get_or_create(
                produto_codigo=produto_codigo,
                empresa=str(pedido.pedi_empr),
                filial=str(pedido.pedi_fili),
                defaults={'saldo_estoque': Decimal('0.00')},
            )
            saldo.saldo_estoque += Decimal(str(saida.said_quan or 0))
            saldo.save(using=banco, update_fields=["saldo_estoque"])

            saida.said_obse = f"{base_obse} - REVERTIDA"
            saida.save(using=banco, update_fields=["said_obse"])
            processado = True

        return {'sucesso': True, 'processado': processado}

    @staticmethod
    def pedido_cancela_nao_exclui(banco: str, empresa: int = 1) -> bool:
        return True
    @staticmethod
    def _proximo_pedido_numero(banco: str, pedi_empr: int, pedi_fili: int) -> int:
        # Número do pedido precisa ser único globalmente, pois é a PK.
        ultimo = (
            PedidoVenda.objects.using(banco)
            .order_by('-pedi_nume')
            .first()
        )
        return (ultimo.pedi_nume + 1) if ultimo else 1

    @transaction.atomic
    @staticmethod
    def create_pedido_venda(banco: str, pedido_data: dict, itens_data: list, pedi_tipo_oper: str = 'VENDA', request=None):
        pedi_empr = int(pedido_data.get('pedi_empr'))
        pedi_fili = int(pedido_data.get('pedi_fili'))

        # Define número do pedido e garante unicidade global (PK)
        numero = pedido_data.get('pedi_nume')
        if numero is None or numero == "":
            numero = PedidoVendaService._proximo_pedido_numero(banco, pedi_empr, pedi_fili)
        try:
            numero = int(numero)
        except Exception:
            numero = PedidoVendaService._proximo_pedido_numero(banco, pedi_empr, pedi_fili)
        pedido_existente = PedidoVenda.objects.using(banco).filter(
            pedi_empr=pedi_empr,
            pedi_fili=pedi_fili,
            pedi_nume=numero,
        ).first()
        if pedido_existente:
            return PedidoVendaService.update_pedido_venda(
                banco=banco,
                pedido=pedido_existente,
                pedido_updates=pedido_data,
                itens_data=itens_data,
                pedi_tipo_oper=pedi_tipo_oper,
                request=request,
            )

        while PedidoVenda.objects.using(banco).filter(pedi_nume=numero).exists():
            numero += 1
        pedido_data['pedi_nume'] = numero

        # Remover campo não persistente
        pedido_data.pop('tipo_oper', None)
        # Cria o pedido
        pedido = PedidoVenda.objects.using(banco).create(**pedido_data)

        # Cria os itens com cálculos de subtotal e total
        itens_criados = []
        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False
        PedidoVendaService.logger.debug(
            "[PedidoService.create] Início: pedi_nume=%s pedi_desc=%s",
            getattr(pedido, 'pedi_nume', None), pedido_data.get('pedi_desc')
        )
        for idx, item_data in enumerate(itens_data, start=1):
            # cálculos
            iped_quan = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item_data.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if iped_desc and iped_desc > 0:
                any_item_discount = True

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            PedidoVendaService.logger.debug(
                "[PedidoService.create] Item %d: quan=%s unit=%s desc=%s subtotal=%s total=%s",
                idx, iped_quan, iped_unit, iped_desc, subtotal_bruto, total_item
            )

            item = Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean,
            )
            try:
                uf_origem = pedido.get_uf_origem(banco)
                uf_destino = getattr(pedido.cliente, 'enti_esta', None) or ''
                
                motor = MotorFiscal(banco=banco)
                
                ctx = FiscalContexto(
                uf_origem=uf_origem or '',
                uf_destino=uf_destino or '',
                produto=item.produto,
                empresa_id=pedido.pedi_empr,
                filial_id=pedido.pedi_fili,   # <-- adicionar
                banco=banco,                   # <-- adicionar
                regime=None,                   # <-- adicionar (None usa o padrão do engine)
)
                
                pacote = motor.calcular_item(       # <-- apenas ctx, item e tipo_oper
                    ctx=ctx,
                    item=item,
                    tipo_oper=pedi_tipo_oper or 'VENDA',
                )
                
                motor.aplicar_no_item(item, pacote)  # <-- substitui todos os hasattr manuais
                item.save(using=banco)

            except Exception as e:
                PedidoVendaService.logger.exception(
                    "[PedidoService.create] erro fiscal item=%s tipo=%s uf_origem=%s uf_destino=%s err=%s",
                    idx, pedi_tipo_oper, uf_origem, uf_destino, e
                )
            itens_criados.append(item)

        # Cálculo dos totais do pedido (alinhado ao serializer)
        pedido_desc_val = PedidoVendaService._to_decimal(pedido_data.get('pedi_desc', 0))
        if pedido_desc_val > 0 and any_item_discount:
            PedidoVendaService.logger.error(
                "[PedidoService.create] Conflito de descontos: desconto_total=%s e desconto_por_item presente",
                pedido_desc_val
            )
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        pedido.pedi_topr = subtotal_sum
        if any_item_discount:
            # Desconto veio dos itens
            pedido.pedi_desc = subtotal_sum - total_items_sum
            pedido.pedi_tota = total_items_sum
        else:
            # Desconto no total
            pedido.pedi_desc = pedido_desc_val
            pedido.pedi_tota = subtotal_sum - pedido_desc_val

        # Liquido (opcional): igual ao total final
        pedido.pedi_liqu = pedido.pedi_tota
        resultado = verificar_baixa_estoque_pedido(pedi_empr, pedi_fili, banco=banco)
        PedidoVendaService.logger.debug(
            "[PedidoService] verificar_baixa_estoque_pedido empr=%s fili=%s resultado=%s",
            pedi_empr, pedi_fili, resultado
        )
        if resultado:
            PedidoVendaService.logger.debug(
                "[PedidoService.create] Iniciando baixa de %d itens", len(itens_data or [])
            )
            itens_agrupados = {}
            for item_data in (itens_data or []):
                try:
                    prod_norm = PedidoVendaService._normalizar_codigo_produto(banco, pedido, item_data.get('iped_prod'))
                    if not prod_norm:
                        continue
                    qtd = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0), default='0.00')
                    unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0), default='0.00')
                    total = (unit * abs(qtd)).quantize(Decimal('0.01'))

                    if prod_norm not in itens_agrupados:
                        itens_agrupados[prod_norm] = {
                            'iped_prod': prod_norm,
                            'iped_quan': Decimal('0.00'),
                            'iped_tota': Decimal('0.00'),
                        }
                    itens_agrupados[prod_norm]['iped_quan'] += abs(qtd)
                    itens_agrupados[prod_norm]['iped_tota'] += total
                except Exception as e:
                    PedidoVendaService.logger.exception(
                        "[PedidoService.create] erro ao baixar item=%s err=%s",
                        item_data.get('iped_prod', None), e
                    )
            for item_data_dict in itens_agrupados.values():
                try:
                    PedidoVendaService._baixar_item_data(pedido, item_data_dict, banco, request=request)
                except Exception as e:
                    PedidoVendaService.logger.exception(
                        "[PedidoService.create] erro ao baixar item=%s err=%s",
                        item_data_dict.get('iped_prod', None), e
                    )

            

        PedidoVendaService.logger.debug(
            "[PedidoService.create] Fim: pedi_nume=%s subtotal=%s desc=%s total=%s",
            getattr(pedido, 'pedi_nume', None), pedido.pedi_topr, pedido.pedi_desc, pedido.pedi_tota
        )

        return pedido

    
    @transaction.atomic
    @staticmethod
    def update_pedido_venda(banco: str, pedido: PedidoVenda, pedido_updates: dict, itens_data: list, pedi_tipo_oper: str | None = None, request=None):
    
        pedi_empr = pedido.pedi_empr
        pedi_fili = pedido.pedi_fili
        try:
            status_novo = int(pedido_updates.get('pedi_stat', getattr(pedido, 'pedi_stat', 0)))
        except Exception:
            status_novo = None

        # Verificar parâmetro de baixa ANTES de qualquer alteração
        deve_baixar = verificar_baixa_estoque_pedido(pedi_empr, pedi_fili, banco=banco)
        PedidoVendaService.logger.debug(
            "[PedidoService.update] deve_baixar=%s empr=%s fili=%s",
            deve_baixar, pedi_empr, pedi_fili
        )

        # Atualiza campos do pedido
        pedido_updates.pop('tipo_oper', None)
        for attr, value in pedido_updates.items():
            setattr(pedido, attr, value)
        pedido.save(using=banco)

        # Remove itens antigos
        Itenspedidovenda.objects.using(banco).filter(
            iped_empr=pedido.pedi_empr,
            iped_fili=pedido.pedi_fili,
            iped_pedi=str(pedido.pedi_nume),
        ).delete()

        # Recria itens
        itens_criados = []
        subtotal_sum = Decimal('0.00')
        total_items_sum = Decimal('0.00')
        any_item_discount = False

        PedidoVendaService.logger.debug(
            "[PedidoService.update] Início: pedi_nume=%s pedi_desc_update=%s",
            getattr(pedido, 'pedi_nume', None), pedido_updates.get('pedi_desc')
        )

        for idx, item_data in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item_data.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)

            subtotal_sum += Decimal(str(subtotal_bruto))
            total_items_sum += Decimal(str(total_item))
            if iped_desc and iped_desc > 0:
                any_item_discount = True

            item_data_clean = item_data.copy()
            item_data_clean.pop('iped_suto', None)
            item_data_clean.pop('iped_tota', None)

            PedidoVendaService.logger.debug(
                "[PedidoService.update] Item %d: quan=%s unit=%s desc=%s subtotal=%s total=%s",
                idx, iped_quan, iped_unit, iped_desc, subtotal_bruto, total_item
            )

            item = Itenspedidovenda.objects.using(banco).create(
                iped_empr=pedido.pedi_empr,
                iped_fili=pedido.pedi_fili,
                iped_item=idx,
                iped_pedi=str(pedido.pedi_nume),
                iped_data=pedido.pedi_data,
                iped_forn=pedido.pedi_forn,
                iped_vend=pedido.pedi_vend,
                iped_unli=subtotal_bruto,
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **item_data_clean,
            )

            try:
                uf_origem = pedido.get_uf_origem(banco)
                uf_destino = getattr(pedido.cliente, 'enti_esta', None) or ''
                motor = MotorFiscal(banco=banco)
                ctx = FiscalContexto(
                    uf_origem=uf_origem or '',
                    uf_destino=uf_destino or '',
                    produto=item.produto,
                    empresa_id=pedido.pedi_empr,
                    filial_id=pedido.pedi_fili,
                    banco=banco,
                    regime=None,
                )
                pacote = motor.calcular_item(ctx=ctx, item=item, tipo_oper=pedi_tipo_oper or 'VENDA')
                motor.aplicar_no_item(item, pacote)
                item.save(using=banco)
            except Exception as e:
                PedidoVendaService.logger.exception(
                    "[PedidoService.update] erro fiscal item=%s tipo=%s err=%s",
                    idx, pedi_tipo_oper, e
                )

            itens_criados.append(item)

        # Cálculo dos totais
        pedido_desc_val = PedidoVendaService._to_decimal(pedido_updates.get('pedi_desc', 0))
        if pedido_desc_val > 0 and any_item_discount:
            raise ValueError("Não é possível aplicar desconto por item e desconto no total simultaneamente.")

        pedido.pedi_topr = subtotal_sum
        if any_item_discount:
            pedido.pedi_desc = subtotal_sum - total_items_sum
            pedido.pedi_tota = total_items_sum
        else:
            pedido.pedi_desc = pedido_desc_val
            pedido.pedi_tota = subtotal_sum - pedido_desc_val

        pedido.pedi_liqu = pedido.pedi_tota

        if status_novo == 4:
            try:
                PedidoVendaService.estornar_estoque_pedido(pedido, banco=banco)
            except Exception as e:
                PedidoVendaService.logger.exception(
                    "[PedidoService.update] erro ao estornar estoque pedido=%s err=%s",
                    getattr(pedido, 'pedi_nume', None), e
                )
        elif deve_baixar:
            if not PedidoVendaService.pedido_tem_baixa(banco, pedido):
                itens_agrupados = {}
                for item_data in (itens_data or []):
                    try:
                        prod_norm = PedidoVendaService._normalizar_codigo_produto(banco, pedido, item_data.get('iped_prod'))
                        if not prod_norm:
                            continue
                        qtd = PedidoVendaService._to_decimal(item_data.get('iped_quan', 0), default='0.00')
                        unit = PedidoVendaService._to_decimal(item_data.get('iped_unit', 0), default='0.00')
                        total = (unit * abs(qtd)).quantize(Decimal('0.01'))

                        if prod_norm not in itens_agrupados:
                            itens_agrupados[prod_norm] = {
                                'iped_prod': prod_norm,
                                'iped_quan': Decimal('0.00'),
                                'iped_tota': Decimal('0.00'),
                            }
                        itens_agrupados[prod_norm]['iped_quan'] += abs(qtd)
                        itens_agrupados[prod_norm]['iped_tota'] += total
                    except Exception as e:
                        PedidoVendaService.logger.exception(
                            "[PedidoService.update] erro ao baixar item=%s err=%s",
                            item_data.get('iped_prod', None), e
                        )
                for item_dict in itens_agrupados.values():
                    try:
                        PedidoVendaService._baixar_item_data(pedido, item_dict, banco, request=request)
                    except Exception as e:
                        PedidoVendaService.logger.exception(
                            "[PedidoService.update] erro ao baixar item=%s err=%s",
                            item_dict.get('iped_prod', None), e
                        )

        pedido.save(using=banco)

        PedidoVendaService.logger.debug(
            "[PedidoService.update] Fim: pedi_nume=%s subtotal=%s desc=%s total=%s",
            getattr(pedido, 'pedi_nume', None), pedido.pedi_topr, pedido.pedi_desc, pedido.pedi_tota
        )

        return pedido

class proximo_pedido_numero:
    @staticmethod
    def get_proximo_numero(banco: str, pedi_empr: int = None, pedi_fili: int = None):
        qs = PedidoVenda.objects.using(banco).all()
        if pedi_empr is not None:
            qs = qs.filter(pedi_empr=pedi_empr)
        if pedi_fili is not None:
            qs = qs.filter(pedi_fili=pedi_fili)
        ultimo_pedido = qs.order_by('-pedi_nume').first()
        return (ultimo_pedido.pedi_nume + 1) if ultimo_pedido else 1

class OrcamentoService:
    logger = logging.getLogger(__name__)

    @staticmethod
    def _proximo_orcamento_numero(banco: str, pedi_empr: int, pedi_fili: int) -> int:
        from Orcamentos.models import Orcamentos
        ultimo = (
            Orcamentos.objects.using(banco)
            .filter(pedi_empr=pedi_empr, pedi_fili=pedi_fili)
            .order_by('-pedi_nume')
            .first()
        )
        proximo = (ultimo.pedi_nume + 1) if ultimo else 1
        while Orcamentos.objects.using(banco).filter(pedi_nume=proximo).exists():
            proximo += 1
        return proximo

    @transaction.atomic
    @staticmethod
    def create_orcamento(banco: str, orcamento_data: dict, itens_data: list):
        from Orcamentos.models import Orcamentos, ItensOrcamento

        pedi_empr = int(orcamento_data.get('pedi_empr'))
        pedi_fili = int(orcamento_data.get('pedi_fili'))

        if not orcamento_data.get('pedi_nume'):
            orcamento_data['pedi_nume'] = OrcamentoService._proximo_orcamento_numero(
                banco, pedi_empr, pedi_fili
            )

        desconto_total = PedidoVendaService._to_decimal(orcamento_data.get('pedi_desc', 0))
        orc = Orcamentos.objects.using(banco).create(**{k: v for k, v in orcamento_data.items() if k != 'pedi_topr' and k != 'pedi_tota'})

        subtotal_sum = Decimal('0.00')
        itens_criados = []
        for idx, item in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)
            subtotal_sum += Decimal(str(subtotal_bruto))

            clean_item = item.copy()
            clean_item.pop('iped_suto', None)
            clean_item.pop('iped_tota', None)

            created = ItensOrcamento.objects.using(banco).create(
                iped_empr=orc.pedi_empr,
                iped_fili=orc.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orc.pedi_nume),
                iped_data=orc.pedi_data,
                iped_forn=getattr(orc, 'pedi_forn', None),
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **clean_item,
            )
            itens_criados.append(created)

        orc.pedi_topr = subtotal_sum
        orc.pedi_desc = desconto_total
        orc.pedi_tota = subtotal_sum - desconto_total
        if orc.pedi_tota < 0:
            orc.pedi_tota = Decimal('0.00')
        orc.save(using=banco)

        return orc

    @transaction.atomic
    @staticmethod
    def update_orcamento(banco: str, orcamento_obj, updates: dict, itens_data: list):
        from Orcamentos.models import ItensOrcamento

        updates = updates.copy()
        desconto_total = PedidoVendaService._to_decimal(updates.pop('pedi_desc', getattr(orcamento_obj, 'pedi_desc', 0)))
        for attr, value in updates.items():
            setattr(orcamento_obj, attr, value)
        orcamento_obj.save(using=banco)

        ItensOrcamento.objects.using(banco).filter(
            iped_empr=orcamento_obj.pedi_empr,
            iped_fili=orcamento_obj.pedi_fili,
            iped_pedi=str(orcamento_obj.pedi_nume),
        ).delete()

        subtotal_sum = Decimal('0.00')
        for idx, item in enumerate(itens_data, start=1):
            iped_quan = PedidoVendaService._to_decimal(item.get('iped_quan', 0))
            iped_unit = PedidoVendaService._to_decimal(item.get('iped_unit', 0))
            iped_desc = PedidoVendaService._to_decimal(item.get('iped_desc', 0))

            subtotal_bruto = calcular_subtotal_item_bruto(iped_quan, iped_unit)
            total_item = calcular_total_item_com_desconto(iped_quan, iped_unit, iped_desc)
            subtotal_sum += Decimal(str(subtotal_bruto))

            clean_item = item.copy()
            clean_item.pop('iped_suto', None)
            clean_item.pop('iped_tota', None)

            ItensOrcamento.objects.using(banco).create(
                iped_empr=orcamento_obj.pedi_empr,
                iped_fili=orcamento_obj.pedi_fili,
                iped_item=idx,
                iped_pedi=str(orcamento_obj.pedi_nume),
                iped_data=orcamento_obj.pedi_data,
                iped_forn=getattr(orcamento_obj, 'pedi_forn', None),
                iped_suto=subtotal_bruto,
                iped_tota=total_item,
                **clean_item,
            )

        orcamento_obj.pedi_topr = subtotal_sum
        orcamento_obj.pedi_desc = desconto_total
        orcamento_obj.pedi_tota = subtotal_sum - desconto_total
        if orcamento_obj.pedi_tota < 0:
            orcamento_obj.pedi_tota = Decimal('0.00')
        orcamento_obj.save(using=banco)

        return orcamento_obj
