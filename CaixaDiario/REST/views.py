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
