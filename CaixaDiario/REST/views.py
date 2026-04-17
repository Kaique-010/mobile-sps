from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.decorator import ModuloRequeridoMixin
from core.utils import get_licenca_db_config
from ..models import Caixageral, Movicaixa


class CaixaViewSet(ModuloRequeridoMixin, viewsets.ViewSet):
    modulo_necessario = 'CaixaDiario'
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def saldo(self, request, *args, **kwargs):
        empresa = request.headers.get('X-Empresa') or request.query_params.get('empresa')
        filial = request.headers.get('X-Filial') or request.query_params.get('filial')
        banco = get_licenca_db_config(self.request) or 'default'
        saldo_inicial = 0.0
        entradas = 0.0
        saidas = 0.0
        saldo_atual = 0.0
        try:
            if empresa and filial:
                qs = Caixageral.objects.using(banco).filter(caix_empr=empresa, caix_fili=filial, caix_aber='A').order_by('-caix_data', '-caix_hora')
                caixa_aberto = qs.first()
                if caixa_aberto:
                    from django.db.models import Sum
                    saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
                    movs = Movicaixa.objects.using(banco).filter(
                        movi_empr=empresa,
                        movi_fili=filial,
                        movi_caix=caixa_aberto.caix_caix,
                        movi_data=caixa_aberto.caix_data
                    )
                    entradas = float(movs.aggregate(Sum('movi_entr')).get('movi_entr__sum') or 0)
                    saidas = float(movs.aggregate(Sum('movi_said')).get('movi_said__sum') or 0)
                    saldo_atual = float(saldo_inicial) + entradas - saidas
        except Exception:
            pass
        return Response({
            'empresa': empresa,
            'filial': filial,
            'saldo_inicial': float(saldo_inicial or 0),
            'entradas': float(entradas or 0),
            'saidas': float(saidas or 0),
            'saldo_atual': float(saldo_atual or 0),
        })

    @action(detail=False, methods=['get'])
    def preco_produto(self, request, *args, **kwargs):
        empresa = request.headers.get('X-Empresa') or request.query_params.get('empresa')
        filial = request.headers.get('X-Filial') or request.query_params.get('filial')
        prod_codi = (request.query_params.get('prod_codi') or request.query_params.get('produto') or '').strip()
        tipo_financeiro = (request.query_params.get('pedi_fina') or request.query_params.get('tipo') or '0')
        promocional = str(request.query_params.get('promocional', '0')).lower() in {'1', 'true', 'sim', 'yes'}
        opcoes = str(request.query_params.get('opcoes', '0')).lower() in {'1', 'true', 'sim', 'yes'}
        modo = (request.query_params.get('modo') or '').strip()

        banco = get_licenca_db_config(self.request) or 'default'
        if not prod_codi:
            return Response({'detail': 'prod_codi é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        if not empresa or not filial:
            return Response({'detail': 'Empresa e Filial são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)

        if not modo:
            modo = 'avista' if str(tipo_financeiro) == '0' else 'prazo'

        try:
            from Produtos.servicos.preco_servico import buscar_preco_normal, obter_valor_preco_normal
            from Produtos.servicos.preco_promocional import buscar_preco_promocional, obter_valor_preco_promocional

            normal = buscar_preco_normal(banco=banco, tabe_empr=str(empresa), tabe_fili=str(filial), tabe_prod=str(prod_codi))
            promo = None
            if promocional or opcoes:
                promo = buscar_preco_promocional(banco=banco, tabe_empr=str(empresa), tabe_fili=str(filial), tabe_prod=str(prod_codi))

            valor_normal = obter_valor_preco_normal(preco=normal, modalidade=modo)
            valor_promo = obter_valor_preco_promocional(preco=promo, modalidade=modo) if promo else None

            if promocional and valor_promo is not None:
                unit_price = float(valor_promo or 0)
                source = 'promocional'
                found = True
            else:
                unit_price = float(valor_normal or 0)
                source = 'normal'
                found = valor_normal is not None

            payload = {'unit_price': unit_price, 'found': bool(found), 'source': source}
            if opcoes or promocional:
                payload['prices'] = {
                    'normal': {
                        'avista': float(obter_valor_preco_normal(preco=normal, modalidade='avista') or 0) if normal else 0,
                        'prazo': float(obter_valor_preco_normal(preco=normal, modalidade='prazo') or 0) if normal else 0,
                    },
                    'promocional': {
                        'avista': float(obter_valor_preco_promocional(preco=promo, modalidade='avista') or 0) if promo else 0,
                        'prazo': float(obter_valor_preco_promocional(preco=promo, modalidade='prazo') or 0) if promo else 0,
                    },
                }
            return Response(payload)
        except Exception:
            return Response({'detail': 'Falha ao obter preço'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def abrir(self, request, *args, **kwargs):
        valor_inicial = float(request.data.get('valor_inicial') or 0)
        return Response({'status': 'aberto', 'valor_inicial': valor_inicial}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def fechar(self, request, *args, **kwargs):
        observacao = (request.data.get('observacao') or '').strip()
        empresa = request.headers.get('X-Empresa') or request.query_params.get('empresa')
        filial = request.headers.get('X-Filial') or request.query_params.get('filial')
        banco = get_licenca_db_config(self.request) or 'default'
        if not empresa or not filial:
            return Response({'detail': 'Empresa e Filial são obrigatórios'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            qs = Caixageral.objects.using(banco).filter(caix_empr=empresa, caix_fili=filial, caix_aber='A').order_by('-caix_data', '-caix_hora')
            caixa_aberto = qs.first()
            if not caixa_aberto:
                return Response({'detail': 'Nenhum caixa aberto encontrado'}, status=status.HTTP_404_NOT_FOUND)
            from django.db.models import Sum
            saldo_inicial = float(getattr(caixa_aberto, 'caix_valo', 0) or getattr(caixa_aberto, 'caix_sald_ini', 0) or 0)
            movs = Movicaixa.objects.using(banco).filter(
                movi_empr=empresa,
                movi_fili=filial,
                movi_caix=caixa_aberto.caix_caix,
                movi_data=caixa_aberto.caix_data
            )
            entradas = float(movs.aggregate(Sum('movi_entr')).get('movi_entr__sum') or 0)
            saidas = float(movs.aggregate(Sum('movi_said')).get('movi_said__sum') or 0)
            saldo_final = float(saldo_inicial) + entradas - saidas
            from datetime import datetime
            caixa_aberto.caix_aber = 'F'
            try:
                caixa_aberto.caix_fech_data = datetime.today().date()
                caixa_aberto.caix_fech_hora = datetime.now().time()
            except Exception:
                pass
            try:
                caixa_aberto.caix_obse_fech = observacao
            except Exception:
                pass
            caixa_aberto.save(using=banco)
            return Response({
                'ok': True,
                'status': 'fechado',
                'observacao': observacao,
                'empresa': empresa,
                'filial': filial,
                'caixa': int(caixa_aberto.caix_caix),
                'saldo_inicial': float(saldo_inicial),
                'entradas': float(entradas),
                'saidas': float(saidas),
                'saldo_final': float(saldo_final),
                'message': 'Caixa fechado com sucesso'
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Falha ao fechar o caixa'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def receber(self, request, *args, **kwargs):
        valor = float(request.data.get('valor') or 0)
        forma = (request.data.get('forma') or 'dinheiro').lower()
        return Response({'ok': True, 'tipo': 'recebimento', 'valor': valor, 'forma': forma}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def venda(self, request, *args, **kwargs):
        total = float(request.data.get('total') or 0)
        pagamento = (request.data.get('pagamento') or 'dinheiro').lower()
        itens = request.data.get('itens') or []
        return Response({'ok': True, 'tipo': 'venda', 'total': total, 'pagamento': pagamento, 'itens': itens}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def cancelar(self, request, *args, **kwargs):
        return Response({'ok': True, 'tipo': 'cancelamento'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def lancamento_entrada(self, request, *args, **kwargs):
        valor = float(request.data.get('valor') or 0)
        forma = (request.data.get('forma') or 'dinheiro').lower()
        return Response({'ok': True, 'tipo': 'entrada', 'valor': valor, 'forma': forma}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def lancamento_saida(self, request, *args, **kwargs):
        valor = float(request.data.get('valor') or 0)
        forma = (request.data.get('forma') or 'dinheiro').lower()
        return Response({'ok': True, 'tipo': 'saida', 'valor': valor, 'forma': forma}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def emitir_cupom(self, request, *args, **kwargs):
        numero_venda = request.data.get('numero_venda')
        cpfcnpj = (request.data.get('cpfcnpj') or '').strip()
        if not numero_venda:
            return Response({'detail': 'Número da venda é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'tipo': 'cupom', 'numero_venda': numero_venda, 'cpfcnpj': cpfcnpj}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def emitir_nfce(self, request, *args, **kwargs):
        numero_venda = request.data.get('numero_venda')
        cpfcnpj = (request.data.get('cpfcnpj') or '').strip()
        if not numero_venda:
            return Response({'detail': 'Número da venda é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'tipo': 'nfce', 'numero_venda': numero_venda, 'cpfcnpj': cpfcnpj}, status=status.HTTP_200_OK)
