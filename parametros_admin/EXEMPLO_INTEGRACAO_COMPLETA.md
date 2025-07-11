# Exemplo de Integração Completa dos Decoradores

Este arquivo mostra exemplos práticos de como integrar os decoradores de parâmetros nas ViewSets existentes do sistema.

## 1. Integração em Entradas de Estoque

### Arquivo: `Entradas_Estoque/views.py`

```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from parametros_admin.decorators import (
    parametros_estoque_completo,
    validar_dados_obrigatorios,
    log_operacao_parametros
)
from .models import EntradaEstoque, ItensEntrada
from .serializers import EntradaEstoqueSerializer, ItensEntradaSerializer

class EntradaEstoqueViewSet(ModelViewSet):
    queryset = EntradaEstoque.objects.all()
    serializer_class = EntradaEstoqueSerializer
    
    @parametros_estoque_completo(operacao='entrada')
    @validar_dados_obrigatorios(['enes_empr', 'enes_fili', 'enes_forn'])
    def create(self, request, *args, **kwargs):
        """
        Criar entrada de estoque com parâmetros aplicados automaticamente
        """
        # Os parâmetros já foram verificados pelo decorator
        # request.parametros_estoque contém todos os parâmetros
        # request.empresa_id e request.filial_id estão disponíveis
        
        # Verificar se entrada automática está habilitada
        if not request.parametros_estoque.get('entrada_automatica_estoque', {}).get('ativo', False):
            return Response(
                {'erro': 'Entrada automática de estoque está desabilitada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Processar entrada usando utils
        from parametros_admin.utils_estoque import processar_entrada_estoque
        
        try:
            resultado = processar_entrada_estoque(request.data, request)
            
            if resultado['sucesso']:
                # Criar entrada normalmente
                response = super().create(request, *args, **kwargs)
                
                # Adicionar informações do processamento
                if hasattr(response, 'data'):
                    response.data.update({
                        'processamento': resultado,
                        'custo_calculado': resultado.get('custo_calculado', False),
                        'estoque_atualizado': resultado.get('estoque_atualizado', False)
                    })
                
                return response
            else:
                return Response(
                    {'erro': resultado['erro']},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'erro': f'Erro ao processar entrada: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @parametros_estoque_completo(operacao='entrada')
    @action(detail=True, methods=['post'])
    def calcular_custo_automatico(self, request, pk=None):
        """
        Calcular custo automático baseado nos parâmetros
        """
        entrada = self.get_object()
        
        # Verificar se cálculo automático está habilitado
        if not request.parametros_estoque.get('calculo_automatico_custo', {}).get('ativo', False):
            return Response(
                {'erro': 'Cálculo automático de custo está desabilitado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from parametros_admin.utils_estoque import calcular_custo_automatico
        
        resultado = calcular_custo_automatico(
            entrada.enes_codi,
            request.empresa_id,
            request.filial_id,
            request
        )
        
        return Response({
            'custo_calculado': resultado['custo_medio'],
            'produtos_atualizados': resultado['produtos_atualizados']
        })

class ItensEntradaViewSet(ModelViewSet):
    queryset = ItensEntrada.objects.all()
    serializer_class = ItensEntradaSerializer
    
    @parametros_estoque_completo(operacao='entrada')
    def create(self, request, *args, **kwargs):
        """
        Criar item de entrada com verificações de parâmetros
        """
        # Verificar estoque mínimo se habilitado
        if request.parametros_estoque.get('alerta_estoque_minimo', {}).get('ativo', False):
            produto_codigo = request.data.get('iene_prod')
            quantidade = request.data.get('iene_quan', 0)
            
            from parametros_admin.utils_estoque import verificar_estoque_minimo
            
            alerta = verificar_estoque_minimo(
                produto_codigo,
                request.empresa_id,
                request.filial_id,
                request
            )
            
            if alerta['abaixo_minimo']:
                # Adicionar alerta na resposta
                response = super().create(request, *args, **kwargs)
                if hasattr(response, 'data'):
                    response.data['alerta_estoque'] = alerta
                return response
        
        return super().create(request, *args, **kwargs)
```

## 2. Integração em Saídas de Estoque

### Arquivo: `Saidas_Estoque/views.py`

```python
from parametros_admin.decorators import parametros_estoque_completo
from .models import SaidaEstoque, ItensSaida
from .serializers import SaidaEstoqueSerializer

class SaidaEstoqueViewSet(ModelViewSet):
    queryset = SaidaEstoque.objects.all()
    serializer_class = SaidaEstoqueSerializer
    
    @parametros_estoque_completo(operacao='saida')
    def create(self, request, *args, **kwargs):
        """
        Criar saída de estoque com validações automáticas
        """
        # Verificar se saída automática está habilitada
        if not request.parametros_estoque.get('saida_automatica_estoque', {}).get('ativo', False):
            return Response(
                {'erro': 'Saída automática de estoque está desabilitada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # O decorator já verificou estoque negativo se necessário
        # Processar saída normalmente
        return super().create(request, *args, **kwargs)
    
    @parametros_estoque_completo(operacao='saida')
    @action(detail=True, methods=['post'])
    def reverter_saida(self, request, pk=None):
        """
        Reverter saída de estoque
        """
        saida = self.get_object()
        
        # Verificar se volta de estoque está habilitada
        if not request.parametros_estoque.get('pedido_volta_estoque', {}).get('ativo', False):
            return Response(
                {'erro': 'Volta de estoque está desabilitada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from parametros_admin.utils_estoque import reverter_saida_estoque
        
        resultado = reverter_saida_estoque(
            saida.said_codi,
            request.empresa_id,
            request.filial_id,
            request
        )
        
        if resultado['sucesso']:
            return Response({
                'status': 'Saída revertida com sucesso',
                'itens_revertidos': resultado['itens_revertidos']
            })
        else:
            return Response(
                {'erro': resultado['erro']},
                status=status.HTTP_400_BAD_REQUEST
            )
```

## 3. Integração em Pedidos

### Arquivo: `Pedidos/views.py`

```python
from parametros_admin.decorators import (
    parametros_pedidos_completo,
    validar_dados_obrigatorios
)
from .models import Pedido, ItensPedido
from .serializers import PedidoSerializer

class PedidosViewSet(ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    
    @parametros_pedidos_completo
    @validar_dados_obrigatorios(['pedi_empr', 'pedi_fili', 'pedi_clie'])
    def create(self, request, *args, **kwargs):
        """
        Criar pedido com parâmetros aplicados automaticamente
        """
        # Processar pedido completo com parâmetros
        from parametros_admin.utils_pedidos import processar_pedido_completo
        
        itens_data = request.data.get('itens', [])
        pedido_data = request.data.copy()
        
        try:
            resultado = processar_pedido_completo(pedido_data, itens_data, request)
            
            if resultado['pedido_valido']:
                # Atualizar dados com preços calculados
                for i, item_resultado in enumerate(resultado['itens_processados']):
                    if i < len(itens_data):
                        itens_data[i].update({
                            'iped_unit': item_resultado['preco_unitario'],
                            'iped_desc': item_resultado.get('desconto_aplicado', 0),
                            'iped_tota': item_resultado['valor_final']
                        })
                
                request.data['itens'] = itens_data
                
                # Criar pedido normalmente
                response = super().create(request, *args, **kwargs)
                
                # Adicionar informações do processamento
                if hasattr(response, 'data'):
                    response.data.update({
                        'processamento': resultado,
                        'alertas': resultado.get('alertas', [])
                    })
                
                return response
            else:
                return Response(
                    {'erro': 'Pedido inválido', 'detalhes': resultado.get('erros', [])},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'erro': f'Erro ao processar pedido: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @parametros_pedidos_completo
    @action(detail=True, methods=['post'])
    def cancelar_pedido(self, request, pk=None):
        """
        Cancelar pedido com volta de estoque se habilitada
        """
        pedido = self.get_object()
        
        from parametros_admin.utils_pedidos import cancelar_pedido_com_volta_estoque
        
        resultado = cancelar_pedido_com_volta_estoque(
            pedido.pedi_codi,
            request.empresa_id,
            request.filial_id,
            request
        )
        
        if resultado['cancelamento_ok']:
            return Response({
                'status': 'Pedido cancelado com sucesso',
                'volta_estoque': resultado['volta_estoque'],
                'itens_revertidos': resultado.get('itens_revertidos', [])
            })
        else:
            return Response(
                {'erro': resultado['erro']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def calcular_preco_produto(self, request, pk=None):
        """
        Calcular preço de produto baseado nos parâmetros
        """
        produto_codigo = request.query_params.get('produto_codigo')
        tipo_preco = request.query_params.get('tipo_preco', 'normal')
        
        if not produto_codigo:
            return Response(
                {'erro': 'produto_codigo é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from parametros_admin.utils_pedidos import obter_preco_produto
        
        preco = obter_preco_produto(
            produto_codigo,
            request.empresa_id or request.data.get('empresa_id'),
            request.filial_id or request.data.get('filial_id'),
            request,
            tipo_preco
        )
        
        return Response({
            'produto_codigo': produto_codigo,
            'preco': preco,
            'tipo_preco': tipo_preco
        })
```

## 4. Integração em Orçamentos

### Arquivo: `Orcamentos/views.py`

```python
from parametros_admin.decorators import parametros_orcamentos_completo
from .models import Orcamento, ItensOrcamento
from .serializers import OrcamentoSerializer

class OrcamentosViewSet(ModelViewSet):
    queryset = Orcamento.objects.all()
    serializer_class = OrcamentoSerializer
    
    @parametros_orcamentos_completo
    def create(self, request, *args, **kwargs):
        """
        Criar orçamento com parâmetros aplicados automaticamente
        """
        # Data de validade já foi calculada pelo decorator
        # request.data['data_validade'] está preenchida
        
        # Processar orçamento completo
        from parametros_admin.utils_orcamentos import processar_orcamento_completo
        
        itens_data = request.data.get('itens', [])
        orcamento_data = request.data.copy()
        
        try:
            resultado = processar_orcamento_completo(orcamento_data, itens_data, request)
            
            if resultado['orcamento_valido']:
                # Atualizar dados com preços calculados
                for i, item_resultado in enumerate(resultado['itens_processados']):
                    if i < len(itens_data):
                        itens_data[i].update({
                            'iorc_unit': item_resultado['preco_unitario'],
                            'iorc_desc': item_resultado.get('desconto_aplicado', 0),
                            'iorc_tota': item_resultado['valor_final']
                        })
                
                request.data['itens'] = itens_data
                request.data['orc_vali'] = resultado['data_validade']
                
                # Criar orçamento normalmente
                response = super().create(request, *args, **kwargs)
                
                # Adicionar informações do processamento
                if hasattr(response, 'data'):
                    response.data.update({
                        'processamento': resultado,
                        'alertas': resultado.get('alertas', []),
                        'data_validade': resultado['data_validade']
                    })
                
                return response
            else:
                return Response(
                    {'erro': 'Orçamento inválido', 'detalhes': resultado.get('erros', [])},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'erro': f'Erro ao processar orçamento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @parametros_orcamentos_completo
    @action(detail=True, methods=['post'])
    def converter_para_pedido(self, request, pk=None):
        """
        Converter orçamento para pedido
        """
        from parametros_admin.utils_orcamentos import converter_orcamento_para_pedido
        
        resultado = converter_orcamento_para_pedido(pk, request)
        
        if resultado['conversao_ok']:
            return Response({
                'status': 'Orçamento convertido com sucesso',
                'orcamento_id': resultado['orcamento_id'],
                'pedido_resultado': resultado['resultado_pedido']
            })
        else:
            return Response(
                {'erro': resultado['erro']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def listar_vencidos(self, request):
        """
        Listar orçamentos vencidos
        """
        empresa_id = request.query_params.get('empresa_id')
        filial_id = request.query_params.get('filial_id')
        
        if not empresa_id or not filial_id:
            return Response(
                {'erro': 'empresa_id e filial_id são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from parametros_admin.utils_orcamentos import listar_orcamentos_vencidos
        
        orcamentos_vencidos = listar_orcamentos_vencidos(
            int(empresa_id), int(filial_id), request
        )
        
        return Response({
            'orcamentos_vencidos': orcamentos_vencidos,
            'total': len(orcamentos_vencidos)
        })
```

## 5. Middleware Personalizado (Opcional)

Para aplicar parâmetros globalmente:

### Arquivo: `parametros_admin/middleware.py`

```python
from django.utils.deprecation import MiddlewareMixin
from .utils_estoque import obter_parametros_estoque
from .utils_pedidos import obter_parametros_pedidos
from .utils_orcamentos import obter_parametros_orcamentos

class ParametrosMiddleware(MiddlewareMixin):
    """
    Middleware para carregar parâmetros automaticamente
    """
    
    def process_request(self, request):
        # Só processar para APIs específicas
        if not request.path.startswith('/api/'):
            return None
        
        # Obter empresa e filial do usuário ou request
        empresa_id = getattr(request.user, 'empresa_id', None)
        filial_id = getattr(request.user, 'filial_id', None)
        
        if empresa_id and filial_id:
            # Carregar parâmetros baseado na URL
            if 'estoque' in request.path:
                request.parametros_sistema = obter_parametros_estoque(
                    empresa_id, filial_id, request
                )
            elif 'pedidos' in request.path:
                request.parametros_sistema = obter_parametros_pedidos(
                    empresa_id, filial_id, request
                )
            elif 'orcamentos' in request.path:
                request.parametros_sistema = obter_parametros_orcamentos(
                    empresa_id, filial_id, request
                )
        
        return None
```

### Adicionar no `settings.py`:

```python
MIDDLEWARE = [
    # ... outros middlewares
    'parametros_admin.middleware.ParametrosMiddleware',
]
```

## 6. Testes de Integração

### Arquivo: `parametros_admin/tests_integracao.py`

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import ParametroSistema, Modulo

class TestIntegracaoParametros(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.user.empresa_id = 1
        self.user.filial_id = 1
        
        # Criar módulo de teste
        self.modulo = Modulo.objects.create(
            modu_nome='Estoque',
            modu_desc='Módulo de Estoque'
        )
        
        # Criar parâmetro de teste
        ParametroSistema.objects.create(
            para_empr=1,
            para_fili=1,
            para_modu=self.modulo,
            para_nome='entrada_automatica_estoque',
            para_valo='true',
            para_desc='Teste',
            para_ativ=True,
            para_tipo='BOOLEAN'
        )
    
    def test_decorator_estoque_aplicado(self):
        """
        Testar se decorator de estoque é aplicado corretamente
        """
        self.client.force_authenticate(user=self.user)
        
        data = {
            'empresa_id': 1,
            'filial_id': 1,
            'produto_codigo': 'PROD001',
            'quantidade': 10
        }
        
        # Simular endpoint que usa decorator
        response = self.client.post('/api/estoque/entrada/', data)
        
        # Verificar se parâmetros foram aplicados
        self.assertIn('parametros_aplicados', response.data)
        self.assertTrue(
            response.data['parametros_aplicados']['estoque']['entrada_automatica_estoque']
        )
    
    def test_validacao_estoque_negativo(self):
        """
        Testar validação de estoque negativo
        """
        # Criar parâmetro que não permite estoque negativo
        ParametroSistema.objects.create(
            para_empr=1,
            para_fili=1,
            para_modu=self.modulo,
            para_nome='permitir_estoque_negativo',
            para_valo='false',
            para_desc='Teste',
            para_ativ=True,
            para_tipo='BOOLEAN'
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'empresa_id': 1,
            'filial_id': 1,
            'produto_codigo': 'PROD001',
            'quantidade': 1000  # Quantidade maior que estoque
        }
        
        response = self.client.post('/api/estoque/saida/', data)
        
        # Deve retornar erro de estoque insuficiente
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('erro', response.data)
```

## 7. Configuração de Produção

### Arquivo: `deploy/configuracao_parametros.py`

```python
"""
Script para configurar parâmetros em produção
"""

import os
import django
from django.core.management.base import BaseCommand

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from parametros_admin.models import ParametroSistema, Modulo

def configurar_parametros_producao():
    """
    Configurar parâmetros para ambiente de produção
    """
    
    # Parâmetros mais restritivos para produção
    parametros_producao = {
        'permitir_estoque_negativo': 'false',
        'validar_estoque_pedido': 'true',
        'alerta_estoque_minimo': 'true',
        'desconto_pedido': 'false',  # Mais restritivo
        'baixa_estoque_orcamento': 'false',
        'conversao_automatica_pedido': 'false'
    }
    
    # Aplicar para todas as empresas/filiais
    for param_nome, valor in parametros_producao.items():
        ParametroSistema.objects.filter(
            para_nome=param_nome
        ).update(
            para_valo=valor,
            para_ativ=True
        )
    
    print("Parâmetros de produção configurados com sucesso!")

if __name__ == '__main__':
    configurar_parametros_producao()
```

Esta integração completa mostra como usar os decoradores e utils em todas as ViewSets do sistema, garantindo que os parâmetros administrativos sejam aplicados de forma consistente e automática.