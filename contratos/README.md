# App Contratos

## Visão Geral

O app **contratos** é responsável pela gestão de contratos de vendas da empresa. Este módulo permite criar, controlar e gerenciar contratos comerciais com clientes, incluindo produtos, quantidades, preços, condições fiscais e de entrega. É uma ferramenta essencial para vendas programadas e controle de entregas futuras.

## Funcionalidades Principais

- **Gestão de Contratos**: Criação e controle de contratos de vendas
- **Controle de Produtos**: Definição de produtos, quantidades e preços contratuais
- **Gestão de Entregas**: Controle de entregas parciais e saldos
- **Configurações Fiscais**: Definição de CST, alíquotas e CFOP
- **Flexibilidade Comercial**: Permissões para alterações de preços e clientes
- **Integração com Pedidos**: Vinculação com sistema de pedidos
- **Controle de Vencimento**: Gestão de prazos contratuais
- **Auditoria**: Rastreabilidade de alterações

## Modelos

### Contratosvendas

Modelo principal que representa um contrato de venda.

```python
class Contratosvendas(models.Model):
    # Identificação
    cont_empr = models.IntegerField()                    # Código da empresa
    cont_fili = models.IntegerField()                    # Código da filial
    cont_cont = models.IntegerField(primary_key=True)    # Número do contrato
    cont_data = models.DateField()                       # Data do contrato
    cont_clie = models.IntegerField()                    # Código do cliente
    
    # Produto e quantidades
    cont_prod = models.CharField(max_length=20)          # Código do produto
    cont_quan = models.DecimalField(max_digits=15, decimal_places=3)  # Quantidade contratada
    cont_unit = models.DecimalField(max_digits=15, decimal_places=6)  # Preço unitário
    cont_tota = models.DecimalField(max_digits=15, decimal_places=2)  # Valor total
    cont_entr = models.DecimalField(max_digits=15, decimal_places=3)  # Quantidade entregue
    cont_sald = models.DecimalField(max_digits=15, decimal_places=3)  # Saldo a entregar
    
    # Informações fiscais
    cont_cst_icms = models.CharField(max_length=3)       # CST ICMS
    cont_redu_icms = models.DecimalField(max_digits=5, decimal_places=2)  # Redução ICMS
    cont_aliq_icms = models.DecimalField(max_digits=5, decimal_places=2)  # Alíquota ICMS
    cont_cst_pis = models.CharField(max_length=2)        # CST PIS
    cont_aliq_pis = models.DecimalField(max_digits=5, decimal_places=2)   # Alíquota PIS
    cont_cst_cofi = models.CharField(max_length=2)       # CST COFINS
    cont_aliq_cofi = models.DecimalField(max_digits=5, decimal_places=2)  # Alíquota COFINS
    cont_cfop_esta = models.IntegerField()               # CFOP estadual
    cont_cfop_fora = models.IntegerField()               # CFOP interestadual
    
    # Controle e permissões
    cont_venc = models.DateField()                       # Data de vencimento
    cont_desc = models.CharField(max_length=60)          # Descrição
    cont_perm_alte_clie = models.BooleanField()          # Permite alterar cliente
    cont_perm_alte_unit = models.BooleanField()          # Permite alterar preço
    cont_perm_alte_venc = models.BooleanField()          # Permite alterar vencimento
    
    # Informações adicionais
    cont_info_adic = models.TextField()                  # Informações adicionais
    cont_port = models.IntegerField()                    # Portador
    cont_situ = models.IntegerField()                    # Situação
    cont_form = models.CharField(max_length=2)           # Forma de pagamento
    cont_sem_fina = models.BooleanField()                # Sem financeiro
    
    # Transporte
    cont_tipo_fret = models.IntegerField()               # Tipo de frete
    cont_tran = models.IntegerField()                    # Transportadora
    cont_veic = models.IntegerField()                    # Veículo
    
    # Vinculações
    cont_cont_orig = models.CharField(max_length=20)     # Contrato original
    cont_cond_fina = models.IntegerField()               # Condição financeira
    cont_pedi_nume = models.CharField(max_length=15)     # Número do pedido
    cont_pedi_item = models.IntegerField()               # Item do pedido
```

#### Campos Principais:
- **Identificação**: Empresa, filial, número do contrato
- **Cliente**: Código do cliente e permissões de alteração
- **Produto**: Código, quantidade, preço e totais
- **Controle de Entregas**: Quantidade entregue e saldo
- **Fiscal**: CST, alíquotas e CFOP para diferentes situações
- **Prazos**: Data do contrato e vencimento
- **Flexibilidade**: Permissões para alterações
- **Logística**: Informações de transporte e frete

## Exemplos de Uso

### Criar Novo Contrato

```python
from contratos.models import Contratosvendas
from datetime import date, timedelta
from decimal import Decimal

# Criar contrato de venda
contrato = Contratosvendas.objects.create(
    cont_empr=1,
    cont_fili=1,
    cont_cont=2024001,
    cont_data=date.today(),
    cont_clie=123,
    cont_prod='PROD001',
    cont_quan=Decimal('1000.000'),
    cont_unit=Decimal('25.50'),
    cont_tota=Decimal('25500.00'),
    cont_entr=Decimal('0.000'),
    cont_sald=Decimal('1000.000'),
    cont_venc=date.today() + timedelta(days=90),
    cont_desc='Contrato de fornecimento trimestral',
    cont_cst_icms='000',
    cont_aliq_icms=Decimal('18.00'),
    cont_cfop_esta=5102,
    cont_cfop_fora=6102,
    cont_perm_alte_unit=True,
    cont_perm_alte_venc=False
)
```

### Registrar Entrega Parcial

```python
def registrar_entrega(contrato_numero, quantidade_entregue):
    contrato = Contratosvendas.objects.get(cont_cont=contrato_numero)
    
    # Verificar se há saldo suficiente
    if quantidade_entregue > contrato.cont_sald:
        raise ValueError('Quantidade entregue maior que saldo disponível')
    
    # Atualizar entregas e saldo
    contrato.cont_entr += quantidade_entregue
    contrato.cont_sald -= quantidade_entregue
    contrato.save()
    
    return contrato

# Exemplo de uso
contrato_atualizado = registrar_entrega(2024001, Decimal('250.000'))
print(f'Saldo restante: {contrato_atualizado.cont_sald}')
```

### Consultar Contratos por Cliente

```python
# Contratos ativos de um cliente
contratos_cliente = Contratosvendas.objects.filter(
    cont_clie=123,
    cont_sald__gt=0,  # Com saldo a entregar
    cont_venc__gte=date.today()  # Não vencidos
).order_by('cont_venc')

# Resumo por cliente
def resumo_contratos_cliente(cliente_id):
    from django.db.models import Sum, Count
    
    resumo = Contratosvendas.objects.filter(
        cont_clie=cliente_id
    ).aggregate(
        total_contratos=Count('cont_cont'),
        valor_total=Sum('cont_tota'),
        saldo_entregar=Sum('cont_sald'),
        quantidade_total=Sum('cont_quan')
    )
    
    return resumo
```

### Relatórios de Contratos

```python
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta

# Contratos vencendo nos próximos 30 dias
contratos_vencendo = Contratosvendas.objects.filter(
    cont_venc__lte=date.today() + timedelta(days=30),
    cont_sald__gt=0
).order_by('cont_venc')

# Contratos por produto
def contratos_por_produto(produto_codigo):
    return Contratosvendas.objects.filter(
        cont_prod=produto_codigo
    ).aggregate(
        total_quantidade=Sum('cont_quan'),
        total_entregue=Sum('cont_entr'),
        total_saldo=Sum('cont_sald'),
        valor_total=Sum('cont_tota')
    )

# Performance de entregas
def performance_entregas(data_inicio, data_fim):
    contratos_periodo = Contratosvendas.objects.filter(
        cont_data__range=[data_inicio, data_fim]
    )
    
    return {
        'total_contratos': contratos_periodo.count(),
        'contratos_completos': contratos_periodo.filter(cont_sald=0).count(),
        'contratos_pendentes': contratos_periodo.filter(cont_sald__gt=0).count(),
        'valor_total': contratos_periodo.aggregate(Sum('cont_tota'))['cont_tota__sum'] or 0,
        'percentual_entregue': (
            contratos_periodo.aggregate(Sum('cont_entr'))['cont_entr__sum'] or 0
        ) / (
            contratos_periodo.aggregate(Sum('cont_quan'))['cont_quan__sum'] or 1
        ) * 100
    }
```

### Validações e Controles

```python
# Validar contrato antes de salvar
def validar_contrato(contrato_data):
    # Verificar se cliente existe
    from Entidades.models import Entidades
    if not Entidades.objects.filter(enti_codi=contrato_data['cont_clie']).exists():
        raise ValueError('Cliente não encontrado')
    
    # Verificar se produto existe
    from Produtos.models import Produtos
    if not Produtos.objects.filter(prod_codi=contrato_data['cont_prod']).exists():
        raise ValueError('Produto não encontrado')
    
    # Validar quantidades
    if contrato_data['cont_quan'] <= 0:
        raise ValueError('Quantidade deve ser maior que zero')
    
    # Validar preços
    if contrato_data['cont_unit'] <= 0:
        raise ValueError('Preço unitário deve ser maior que zero')
    
    # Validar datas
    if contrato_data['cont_venc'] <= contrato_data['cont_data']:
        raise ValueError('Data de vencimento deve ser posterior à data do contrato')

# Verificar permissões de alteração
def pode_alterar_preco(contrato):
    return contrato.cont_perm_alte_unit and contrato.cont_sald > 0

def pode_alterar_cliente(contrato):
    return contrato.cont_perm_alte_clie and contrato.cont_entr == 0
```

## Endpoints da API

### Listar Contratos
```http
GET /api/contratos/
GET /api/contratos/?cont_clie=123
GET /api/contratos/?cont_prod=PROD001
GET /api/contratos/?cont_venc__lte=2024-12-31
GET /api/contratos/?cont_sald__gt=0
```

### Criar Contrato
```http
POST /api/contratos/
Content-Type: application/json

{
    "cont_empr": 1,
    "cont_fili": 1,
    "cont_cont": 2024001,
    "cont_data": "2024-01-15",
    "cont_clie": 123,
    "cont_prod": "PROD001",
    "cont_quan": 1000.000,
    "cont_unit": 25.50,
    "cont_tota": 25500.00,
    "cont_venc": "2024-04-15",
    "cont_desc": "Contrato trimestral",
    "cont_cst_icms": "000",
    "cont_aliq_icms": 18.00
}
```

### Registrar Entrega
```http
POST /api/contratos/{numero}/entrega/
Content-Type: application/json

{
    "quantidade": 250.000,
    "data_entrega": "2024-02-15",
    "observacoes": "Entrega parcial conforme programação"
}
```

### Atualizar Contrato
```http
PUT /api/contratos/{numero}/
Content-Type: application/json

{
    "cont_unit": 26.00,
    "cont_tota": 26000.00,
    "cont_desc": "Contrato com reajuste de preço"
}
```

### Relatórios
```http
# Contratos vencendo
GET /api/contratos/vencendo/?dias=30

# Resumo por cliente
GET /api/contratos/resumo-cliente/{cliente_id}/

# Performance de entregas
GET /api/contratos/performance/?data_inicio=2024-01-01&data_fim=2024-03-31

# Contratos por produto
GET /api/contratos/por-produto/{produto_codigo}/
```

### Filtros Avançados
```http
# Contratos com saldo
GET /api/contratos/?cont_sald__gt=0

# Contratos vencidos
GET /api/contratos/?cont_venc__lt=2024-01-15

# Contratos por valor
GET /api/contratos/?cont_tota__gte=10000.00

# Contratos com permissão de alteração
GET /api/contratos/?cont_perm_alte_unit=true
```

## Considerações Técnicas

### Banco de Dados
- **Tabela**: `contratosvendas`
- **Chave Primária**: `cont_cont` (número do contrato)
- **Índices Recomendados**:
  - `(cont_empr, cont_fili, cont_cont)` - Unique constraint
  - `cont_clie` - Para consultas por cliente
  - `cont_prod` - Para consultas por produto
  - `cont_venc` - Para controle de vencimentos
  - `cont_data` - Para relatórios por período
  - `cont_sald` - Para contratos com saldo

### Validações
- Quantidade deve ser maior que zero
- Preço unitário deve ser maior que zero
- Data de vencimento posterior à data do contrato
- Cliente e produto devem existir nos cadastros
- Saldo não pode ser negativo
- Quantidade entregue não pode exceder quantidade contratada

### Triggers e Procedures
- Cálculo automático de totais
- Atualização de saldos em entregas
- Controle de numeração sequencial
- Validações de integridade referencial
- Logs de auditoria para alterações
- Alertas para contratos vencendo

### Performance
- Índices otimizados para consultas frequentes
- Agregações para relatórios de performance
- Cache para consultas de resumos
- Paginação para listagens grandes

## Integração com Outros Apps

### Entidades
- Validação de clientes
- Dados para faturamento e entrega
- Histórico comercial

### Produtos
- Validação de produtos
- Controle de disponibilidade
- Informações fiscais padrão

### Pedidos
- Geração de pedidos a partir de contratos
- Vinculação de entregas
- Controle de faturamento

### Contas a Receber
- Geração de títulos conforme entregas
- Controle de condições de pagamento

### Auditoria
- Log de todas as operações
- Rastreabilidade de alterações
- Controle de usuários

## Troubleshooting

### Problemas Comuns

1. **Erro de Saldo Insuficiente**
   ```python
   # Verificar saldo disponível
   def verificar_saldo(contrato_numero, quantidade):
       contrato = Contratosvendas.objects.get(cont_cont=contrato_numero)
       return contrato.cont_sald >= quantidade
   ```

2. **Problemas de Permissão de Alteração**
   ```python
   # Verificar permissões antes de alterar
   def pode_alterar(contrato, campo):
       permissoes = {
           'cliente': contrato.cont_perm_alte_clie and contrato.cont_entr == 0,
           'preco': contrato.cont_perm_alte_unit and contrato.cont_sald > 0,
           'vencimento': contrato.cont_perm_alte_venc
       }
       return permissoes.get(campo, False)
   ```

3. **Inconsistências em Totais**
   ```python
   # Recalcular totais
   def recalcular_totais(contrato):
       contrato.cont_tota = contrato.cont_quan * contrato.cont_unit
       contrato.cont_sald = contrato.cont_quan - contrato.cont_entr
       contrato.save()
   ```

### Logs de Debug
```python
import logging
logger = logging.getLogger('contratos')

# Log de contrato criado
logger.info(f'Contrato criado: {contrato.cont_cont} - Cliente: {contrato.cont_clie} - Produto: {contrato.cont_prod}')

# Log de entrega
logger.info(f'Entrega registrada: Contrato {contrato.cont_cont} - Quantidade: {quantidade}')

# Log de erro
logger.error(f'Erro ao processar contrato: {str(e)}')
```

### Comandos de Manutenção
```bash
# Verificar integridade dos dados
python manage.py shell -c "from contratos.models import Contratosvendas; print(Contratosvendas.objects.count())"

# Recalcular saldos
python manage.py recalcular_saldos_contratos

# Alertar contratos vencendo
python manage.py alertar_contratos_vencendo

# Relatório de performance
python manage.py relatorio_performance_contratos

# Backup de contratos
python manage.py dumpdata contratos > backup_contratos.json
```

### Monitoramento
```python
# Alertas de contratos vencendo
def verificar_contratos_vencendo(dias=30):
    data_limite = date.today() + timedelta(days=dias)
    vencendo = Contratosvendas.objects.filter(
        cont_venc__lte=data_limite,
        cont_sald__gt=0
    ).count()
    
    if vencendo > 0:
        logger.warning(f'{vencendo} contratos vencendo em {dias} dias')
    
    return vencendo

# Monitorar performance de entregas
def monitorar_entregas():
    contratos_ativos = Contratosvendas.objects.filter(cont_sald__gt=0)
    total_saldo = sum(c.cont_sald for c in contratos_ativos)
    
    if total_saldo > 0:
        logger.info(f'Saldo total a entregar: {total_saldo}')
    
    return total_saldo
```

## Conclusão

O app **contratos** é essencial para a gestão comercial da empresa, oferecendo controle completo sobre contratos de vendas, entregas programadas e condições comerciais. Sua integração com outros módulos garante a consistência dos processos de vendas e permite um acompanhamento eficiente do cumprimento dos contratos firmados com clientes.