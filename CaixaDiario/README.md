# App CaixaDiario

Este app gerencia o controle de caixa diário, incluindo abertura, fechamento e movimentações financeiras do caixa.

## Funcionalidades

### 1. Controle de Caixa

- **Abertura de Caixa**: Registro de abertura diária por operador
- **Fechamento de Caixa**: Encerramento com conferência de valores
- **Múltiplos Caixas**: Suporte a vários caixas por filial
- **Controle por Operador**: Rastreamento de responsabilidade
- **Integração ECF**: Suporte a equipamentos fiscais

### 2. Movimentações Financeiras

- **Entradas**: Vendas, recebimentos, sangrias
- **Saídas**: Pagamentos, suprimentos, retiradas
- **Tipos de Movimento**: Classificação detalhada
- **Documentos Fiscais**: Vinculação com notas e cupons
- **Formas de Pagamento**: Dinheiro, cheques, cartões

### 3. Controles Operacionais

- **Sangria**: Retirada de valores excedentes
- **Suprimento**: Reforço de troco
- **Conferência**: Validação de saldos
- **Auditoria**: Rastreamento completo de operações
- **Relatórios**: Demonstrativos financeiros

## Estrutura dos Dados

### Modelo Caixageral

```python
class Caixageral(models.Model):
    # Identificação
    caix_empr = models.IntegerField()  # Empresa
    caix_fili = models.IntegerField()  # Filial
    caix_caix = models.IntegerField()  # Número do caixa
    caix_data = models.DateField(primary_key=True)  # Data
    
    # Controle de Operação
    caix_hora = models.TimeField(auto_now_add=True)  # Hora de abertura
    caix_aber = models.CharField(max_length=1)  # Status abertura (S/N)
    caix_oper = models.IntegerField()  # Operador responsável
    
    # Equipamentos
    caix_ecf = models.CharField(max_length=30)  # Série do ECF
    caix_orig = models.IntegerField()  # Origem da operação
    caix_valo = models.DecimalField(max_digits=15, decimal_places=2)  # Valor inicial
    
    # Fechamento
    caix_fech_data = models.DateField()  # Data do fechamento
    caix_fech_hora = models.TimeField()  # Hora do fechamento
    caix_obse_fech = models.TextField()  # Observações do fechamento
    
    # Auditoria
    caix_ctrl = models.IntegerField()  # Controle interno
    _log_data = models.DateField()  # Log de data
    _log_time = models.TimeField()  # Log de hora
```

### Modelo Movicaixa

```python
class Movicaixa(models.Model):
    # Identificação
    movi_empr = models.IntegerField(primary_key=True)  # Empresa
    movi_fili = models.IntegerField()  # Filial
    movi_caix = models.IntegerField()  # Caixa
    movi_data = models.DateField()  # Data do movimento
    movi_ctrl = models.IntegerField()  # Controle sequencial
    
    # Valores
    movi_entr = models.DecimalField(max_digits=15, decimal_places=2)  # Entrada
    movi_said = models.DecimalField(max_digits=15, decimal_places=2)  # Saída
    movi_tipo = models.IntegerField()  # Tipo de movimento
    
    # Detalhes da Operação
    movi_obse = models.TextField()  # Observações
    movi_oper = models.IntegerField()  # Operador
    movi_hora = models.TimeField()  # Hora do movimento
    
    # Vinculações
    movi_nume_vend = models.IntegerField()  # Pedido de venda
    movi_clie = models.IntegerField()  # Cliente
    movi_vend = models.IntegerField()  # Vendedor
    movi_cont = models.IntegerField()  # Conta contábil
    
    # Documentos Fiscais
    movi_seri_nota = models.CharField(max_length=3)  # Série da nota
    movi_nume_nota = models.DecimalField()  # Número da nota
    movi_coo = models.DecimalField()  # COO do cupom fiscal
    movi_seri_ecf = models.CharField(max_length=20)  # Série do ECF
    
    # Cheques
    movi_cheq = models.IntegerField()  # Número do cheque
    movi_cheq_banc = models.IntegerField()  # Banco do cheque
    movi_cheq_agen = models.CharField(max_length=15)  # Agência
    movi_cheq_cont = models.CharField(max_length=15)  # Conta
    movi_bomp = models.DateField()  # Bom para (data)
    
    # Controles Especiais
    movi_sang = models.BooleanField()  # Movimento de sangria
    movi_tipo_movi = models.IntegerField()  # Tipo específico
    movi_banc_tran = models.IntegerField()  # Transação bancária
    movi_sequ_tran = models.IntegerField()  # Sequencial da transação
```

## Exemplos de Uso

### 1. Abertura de Caixa

```python
from CaixaDiario.models import Caixageral, Movicaixa
from decimal import Decimal
from datetime import date, time

# Abrir caixa do dia
caixa = Caixageral.objects.create(
    caix_empr=1,
    caix_fili=1,
    caix_caix=1,  # Caixa número 1
    caix_data=date.today(),
    caix_aber='S',  # Aberto
    caix_oper=101,  # Operador
    caix_ecf='ECF001',
    caix_valo=Decimal('200.00'),  # Valor inicial (troco)
    caix_ctrl=1
)

# Registrar movimento de abertura
movimento_abertura = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=1,
    movi_entr=Decimal('200.00'),  # Entrada do troco inicial
    movi_said=Decimal('0.00'),
    movi_tipo=1,  # Tipo: Abertura
    movi_obse='Abertura de caixa - Troco inicial',
    movi_oper=101,
    movi_hora=time(8, 0, 0),  # 08:00
    movi_seri='CAI'
)

print(f"Caixa {caixa.caix_caix} aberto em {caixa.caix_data}")
```

### 2. Registrar Venda

```python
# Registrar venda à vista
venda = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=2,  # Próximo controle
    movi_entr=Decimal('150.00'),  # Valor da venda
    movi_said=Decimal('0.00'),
    movi_tipo=2,  # Tipo: Venda
    movi_obse='Venda à vista - Cupom fiscal',
    movi_oper=101,
    movi_hora=time(10, 30, 0),
    movi_nume_vend=12345,  # Número do pedido
    movi_clie=1001,  # Cliente
    movi_vend=5,  # Vendedor
    movi_coo=Decimal('123456'),  # COO do cupom
    movi_seri_ecf='ECF001',
    movi_seri='CAI'
)

# Registrar venda com cheque
venda_cheque = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=3,
    movi_entr=Decimal('300.00'),
    movi_said=Decimal('0.00'),
    movi_tipo=3,  # Tipo: Cheque
    movi_obse='Venda com cheque',
    movi_oper=101,
    movi_hora=time(11, 15, 0),
    movi_nume_vend=12346,
    movi_clie=1002,
    movi_cheq=789456,  # Número do cheque
    movi_cheq_banc=341,  # Banco Itaú
    movi_cheq_agen='1234',
    movi_cheq_cont='12345-6',
    movi_bomp=date.today(),  # Bom para hoje
    movi_seri='CHE'
)
```

### 3. Sangria de Caixa

```python
# Realizar sangria (retirada de dinheiro)
sangria = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=4,
    movi_entr=Decimal('0.00'),
    movi_said=Decimal('500.00'),  # Valor retirado
    movi_tipo=4,  # Tipo: Sangria
    movi_obse='Sangria - Excesso de dinheiro no caixa',
    movi_oper=101,
    movi_hora=time(14, 0, 0),
    movi_sang=True,  # Marca como sangria
    movi_codi_admi=201,  # Código do administrador
    movi_seri='SAN'
)

print(f"Sangria realizada: R$ {sangria.movi_said}")
```

### 4. Suprimento de Caixa

```python
# Realizar suprimento (reforço de troco)
suprimento = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=5,
    movi_entr=Decimal('100.00'),  # Valor adicionado
    movi_said=Decimal('0.00'),
    movi_tipo=5,  # Tipo: Suprimento
    movi_obse='Suprimento - Reforço de troco',
    movi_oper=101,
    movi_hora=time(16, 30, 0),
    movi_codi_admi=201,
    movi_seri='SUP'
)
```

### 5. Fechamento de Caixa

```python
from django.db.models import Sum

# Calcular totais do dia
totais = Movicaixa.objects.filter(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today()
).aggregate(
    total_entradas=Sum('movi_entr'),
    total_saidas=Sum('movi_said')
)

saldo_final = (totais['total_entradas'] or Decimal('0.00')) - (totais['total_saidas'] or Decimal('0.00'))

# Fechar caixa
caixa_fechamento = Caixageral.objects.get(
    caix_empr=1,
    caix_fili=1,
    caix_caix=1,
    caix_data=date.today()
)

caixa_fechamento.caix_aber = 'N'  # Fechado
caixa_fechamento.caix_fech_data = date.today()
caixa_fechamento.caix_fech_hora = time(18, 0, 0)
caixa_fechamento.caix_obse_fech = f'Fechamento normal. Saldo final: R$ {saldo_final}'
caixa_fechamento.save()

# Registrar movimento de fechamento
fechamento = Movicaixa.objects.create(
    movi_empr=1,
    movi_fili=1,
    movi_caix=1,
    movi_data=date.today(),
    movi_ctrl=99,  # Controle especial para fechamento
    movi_entr=Decimal('0.00'),
    movi_said=Decimal('0.00'),
    movi_tipo=99,  # Tipo: Fechamento
    movi_obse=f'Fechamento de caixa. Saldo: R$ {saldo_final}',
    movi_oper=101,
    movi_hora=time(18, 0, 0),
    movi_seri='FEC'
)

print(f"Caixa fechado. Saldo final: R$ {saldo_final}")
```

### 6. Relatórios de Caixa

```python
# Relatório de movimentação do dia
def relatorio_caixa_dia(empresa, filial, caixa, data):
    movimentos = Movicaixa.objects.filter(
        movi_empr=empresa,
        movi_fili=filial,
        movi_caix=caixa,
        movi_data=data
    ).order_by('movi_hora')
    
    relatorio = {
        'abertura': None,
        'vendas': [],
        'sangrias': [],
        'suprimentos': [],
        'outros': [],
        'totais': {
            'entradas': Decimal('0.00'),
            'saidas': Decimal('0.00'),
            'saldo': Decimal('0.00')
        }
    }
    
    for mov in movimentos:
        if mov.movi_tipo == 1:  # Abertura
            relatorio['abertura'] = mov
        elif mov.movi_tipo == 2:  # Venda
            relatorio['vendas'].append(mov)
        elif mov.movi_tipo == 4:  # Sangria
            relatorio['sangrias'].append(mov)
        elif mov.movi_tipo == 5:  # Suprimento
            relatorio['suprimentos'].append(mov)
        else:
            relatorio['outros'].append(mov)
        
        relatorio['totais']['entradas'] += mov.movi_entr or Decimal('0.00')
        relatorio['totais']['saidas'] += mov.movi_said or Decimal('0.00')
    
    relatorio['totais']['saldo'] = relatorio['totais']['entradas'] - relatorio['totais']['saidas']
    
    return relatorio

# Relatório por período
def relatorio_periodo(empresa, filial, data_inicio, data_fim):
    from django.db.models import Sum, Count
    
    return Movicaixa.objects.filter(
        movi_empr=empresa,
        movi_fili=filial,
        movi_data__range=[data_inicio, data_fim]
    ).values('movi_data', 'movi_caix').annotate(
        total_entradas=Sum('movi_entr'),
        total_saidas=Sum('movi_said'),
        qtd_movimentos=Count('movi_ctrl')
    ).order_by('movi_data', 'movi_caix')

# Relatório por operador
def relatorio_operador(empresa, filial, operador, data_inicio, data_fim):
    return Movicaixa.objects.filter(
        movi_empr=empresa,
        movi_fili=filial,
        movi_oper=operador,
        movi_data__range=[data_inicio, data_fim]
    ).values('movi_data').annotate(
        total_entradas=Sum('movi_entr'),
        total_saidas=Sum('movi_said'),
        qtd_vendas=Count('movi_ctrl', filter=models.Q(movi_tipo=2))
    ).order_by('movi_data')
```

### 7. Validações e Conferências

```python
# Validar abertura de caixa
def validar_abertura_caixa(empresa, filial, caixa, data):
    caixa_aberto = Caixageral.objects.filter(
        caix_empr=empresa,
        caix_fili=filial,
        caix_caix=caixa,
        caix_data=data,
        caix_aber='S'
    ).exists()
    
    if not caixa_aberto:
        raise ValueError(f"Caixa {caixa} não está aberto para a data {data}")
    
    return True

# Conferir saldo do caixa
def conferir_saldo_caixa(empresa, filial, caixa, data):
    # Buscar valor inicial
    caixa_info = Caixageral.objects.get(
        caix_empr=empresa,
        caix_fili=filial,
        caix_caix=caixa,
        caix_data=data
    )
    
    valor_inicial = caixa_info.caix_valo or Decimal('0.00')
    
    # Calcular movimentações
    totais = Movicaixa.objects.filter(
        movi_empr=empresa,
        movi_fili=filial,
        movi_caix=caixa,
        movi_data=data
    ).exclude(
        movi_tipo=1  # Excluir abertura do cálculo
    ).aggregate(
        entradas=Sum('movi_entr'),
        saidas=Sum('movi_said')
    )
    
    saldo_calculado = valor_inicial + (totais['entradas'] or Decimal('0.00')) - (totais['saidas'] or Decimal('0.00'))
    
    return {
        'valor_inicial': valor_inicial,
        'entradas': totais['entradas'] or Decimal('0.00'),
        'saidas': totais['saidas'] or Decimal('0.00'),
        'saldo_calculado': saldo_calculado
    }

# Detectar inconsistências
def detectar_inconsistencias(empresa, filial, data):
    inconsistencias = []
    
    # Verificar caixas sem fechamento
    caixas_abertos = Caixageral.objects.filter(
        caix_empr=empresa,
        caix_fili=filial,
        caix_data=data,
        caix_aber='S',
        caix_fech_data__isnull=True
    )
    
    for caixa in caixas_abertos:
        inconsistencias.append({
            'tipo': 'caixa_nao_fechado',
            'caixa': caixa.caix_caix,
            'data': caixa.caix_data,
            'operador': caixa.caix_oper
        })
    
    # Verificar movimentos sem caixa aberto
    movimentos_sem_caixa = Movicaixa.objects.filter(
        movi_empr=empresa,
        movi_fili=filial,
        movi_data=data
    ).exclude(
        movi_caix__in=Caixageral.objects.filter(
            caix_empr=empresa,
            caix_fili=filial,
            caix_data=data
        ).values_list('caix_caix', flat=True)
    )
    
    for movimento in movimentos_sem_caixa:
        inconsistencias.append({
            'tipo': 'movimento_sem_caixa',
            'caixa': movimento.movi_caix,
            'controle': movimento.movi_ctrl,
            'valor': movimento.movi_entr or movimento.movi_said
        })
    
    return inconsistencias
```

## API Endpoints

### Caixa Geral
```
GET /api/{licenca}/caixadiario/caixageral/
POST /api/{licenca}/caixadiario/caixageral/
GET /api/{licenca}/caixadiario/caixageral/{data}/
PUT /api/{licenca}/caixadiario/caixageral/{data}/
PATCH /api/{licenca}/caixadiario/caixageral/{data}/
```

### Movimentações
```
GET /api/{licenca}/caixadiario/movimentos/
POST /api/{licenca}/caixadiario/movimentos/
GET /api/{licenca}/caixadiario/movimentos/{id}/
PUT /api/{licenca}/caixadiario/movimentos/{id}/
DELETE /api/{licenca}/caixadiario/movimentos/{id}/
```

### Ações Especiais
```
POST /api/{licenca}/caixadiario/abrir-caixa/
POST /api/{licenca}/caixadiario/fechar-caixa/
POST /api/{licenca}/caixadiario/sangria/
POST /api/{licenca}/caixadiario/suprimento/
GET /api/{licenca}/caixadiario/relatorio-dia/
GET /api/{licenca}/caixadiario/conferencia/
```

### Filtros Disponíveis

#### Caixa Geral
- `caix_empr`: Filtrar por empresa
- `caix_fili`: Filtrar por filial
- `caix_caix`: Filtrar por caixa
- `caix_data`: Filtrar por data
- `caix_aber`: Status (S/N)
- `caix_oper`: Operador

#### Movimentações
- `movi_empr`: Empresa
- `movi_fili`: Filial
- `movi_caix`: Caixa
- `movi_data`: Data (range)
- `movi_tipo`: Tipo de movimento
- `movi_oper`: Operador
- `valor_min`: Valor mínimo
- `valor_max`: Valor máximo

### Exemplos de Requisições
```
GET /api/empresa123/caixadiario/movimentos/?movi_data=2024-01-15&movi_tipo=2
GET /api/empresa123/caixadiario/caixageral/?caix_aber=S
POST /api/empresa123/caixadiario/abrir-caixa/
{
  "empresa": 1,
  "filial": 1,
  "caixa": 1,
  "operador": 101,
  "valor_inicial": 200.00
}
```

## Considerações Técnicas

### Banco de Dados
- **Tabelas**: `caixageral`, `movicaixa`
- **Managed**: False (tabelas não gerenciadas pelo Django)
- **Chaves Compostas**: Múltiplos campos formam chaves únicas

### Índices Recomendados
```sql
-- Caixa Geral
CREATE INDEX idx_caixageral_empresa_filial ON caixageral (caix_empr, caix_fili);
CREATE INDEX idx_caixageral_data ON caixageral (caix_data);
CREATE INDEX idx_caixageral_operador ON caixageral (caix_oper);
CREATE INDEX idx_caixageral_status ON caixageral (caix_aber);

-- Movimentações
CREATE INDEX idx_movicaixa_empresa_filial_caixa ON movicaixa (movi_empr, movi_fili, movi_caix);
CREATE INDEX idx_movicaixa_data ON movicaixa (movi_data);
CREATE INDEX idx_movicaixa_tipo ON movicaixa (movi_tipo);
CREATE INDEX idx_movicaixa_operador ON movicaixa (movi_oper);
CREATE INDEX idx_movicaixa_pedido ON movicaixa (movi_nume_vend);
CREATE INDEX idx_movicaixa_cliente ON movicaixa (movi_clie);
```

### Validações Recomendadas

```python
from django.core.exceptions import ValidationError
from decimal import Decimal

def clean(self):
    # Validar valores
    if hasattr(self, 'movi_entr') and self.movi_entr and self.movi_entr < 0:
        raise ValidationError('Valor de entrada não pode ser negativo')
    
    if hasattr(self, 'movi_said') and self.movi_said and self.movi_said < 0:
        raise ValidationError('Valor de saída não pode ser negativo')
    
    # Validar que não pode ter entrada e saída no mesmo movimento
    if hasattr(self, 'movi_entr') and hasattr(self, 'movi_said'):
        if self.movi_entr and self.movi_said:
            if self.movi_entr > 0 and self.movi_said > 0:
                raise ValidationError('Movimento não pode ter entrada e saída simultaneamente')
    
    # Validar abertura de caixa
    if hasattr(self, 'caix_aber') and self.caix_aber not in ['S', 'N']:
        raise ValidationError('Status de abertura deve ser S ou N')
    
    # Validar valor inicial do caixa
    if hasattr(self, 'caix_valo') and self.caix_valo and self.caix_valo < 0:
        raise ValidationError('Valor inicial do caixa não pode ser negativo')
```

### Triggers e Procedures

```sql
-- Trigger para validar movimentos
CREATE TRIGGER trg_valida_movimento_caixa
BEFORE INSERT ON movicaixa
FOR EACH ROW
BEGIN
    -- Verificar se caixa está aberto
    IF NOT EXISTS (
        SELECT 1 FROM caixageral 
        WHERE caix_empr = NEW.movi_empr 
        AND caix_fili = NEW.movi_fili 
        AND caix_caix = NEW.movi_caix 
        AND caix_data = NEW.movi_data 
        AND caix_aber = 'S'
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Caixa não está aberto para esta data';
    END IF;
    
    -- Gerar controle sequencial
    SET NEW.movi_ctrl = (
        SELECT COALESCE(MAX(movi_ctrl), 0) + 1
        FROM movicaixa 
        WHERE movi_empr = NEW.movi_empr 
        AND movi_fili = NEW.movi_fili 
        AND movi_caix = NEW.movi_caix 
        AND movi_data = NEW.movi_data
    );
END;

-- Procedure para fechamento automático
CREATE PROCEDURE sp_fechar_caixa(
    IN p_empresa INT,
    IN p_filial INT,
    IN p_caixa INT,
    IN p_data DATE,
    IN p_operador INT
)
BEGIN
    DECLARE v_saldo DECIMAL(15,2);
    
    -- Calcular saldo
    SELECT COALESCE(SUM(movi_entr), 0) - COALESCE(SUM(movi_said), 0)
    INTO v_saldo
    FROM movicaixa
    WHERE movi_empr = p_empresa
    AND movi_fili = p_filial
    AND movi_caix = p_caixa
    AND movi_data = p_data;
    
    -- Atualizar caixa
    UPDATE caixageral
    SET caix_aber = 'N',
        caix_fech_data = p_data,
        caix_fech_hora = CURTIME(),
        caix_obse_fech = CONCAT('Fechamento automático. Saldo: R$ ', v_saldo)
    WHERE caix_empr = p_empresa
    AND caix_fili = p_filial
    AND caix_caix = p_caixa
    AND caix_data = p_data;
    
    -- Inserir movimento de fechamento
    INSERT INTO movicaixa (
        movi_empr, movi_fili, movi_caix, movi_data, movi_ctrl,
        movi_entr, movi_said, movi_tipo, movi_obse, movi_oper, movi_hora
    ) VALUES (
        p_empresa, p_filial, p_caixa, p_data, 999,
        0, 0, 99, CONCAT('Fechamento. Saldo: R$ ', v_saldo), p_operador, CURTIME()
    );
END;
```

## Integração com Outros Apps

### Relacionamentos Comuns

```python
# Com Pedidos (Vendas)
class Movicaixa(models.Model):
    pedido = models.ForeignKey(
        'Pedidos.PedidoVenda',
        on_delete=models.PROTECT,
        db_column='movi_nume_vend',
        to_field='pedi_nume',
        null=True,
        blank=True
    )

# Com Entidades (Clientes)
class Movicaixa(models.Model):
    cliente = models.ForeignKey(
        'Entidades.Entidades',
        on_delete=models.PROTECT,
        db_column='movi_clie',
        to_field='enti_clie',
        null=True,
        blank=True
    )

# Com Contas a Receber
class Movicaixa(models.Model):
    conta_receber = models.ForeignKey(
        'contas_a_receber.ContasReceber',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentos_caixa'
    )
```

### Workflows de Integração

```python
# Integração com vendas
def registrar_venda_caixa(pedido_venda, forma_pagamento, valor):
    """Registra venda no caixa automaticamente"""
    
    # Determinar tipo de movimento baseado na forma de pagamento
    tipo_movimento = {
        'dinheiro': 2,
        'cheque': 3,
        'cartao_debito': 6,
        'cartao_credito': 7,
        'pix': 8
    }.get(forma_pagamento, 2)
    
    movimento = Movicaixa.objects.create(
        movi_empr=pedido_venda.pedi_empr,
        movi_fili=pedido_venda.pedi_fili,
        movi_caix=1,  # Caixa padrão
        movi_data=pedido_venda.pedi_data,
        movi_entr=valor,
        movi_said=Decimal('0.00'),
        movi_tipo=tipo_movimento,
        movi_obse=f'Venda {forma_pagamento} - Pedido {pedido_venda.pedi_nume}',
        movi_nume_vend=pedido_venda.pedi_nume,
        movi_clie=int(pedido_venda.pedi_forn),
        movi_vend=int(pedido_venda.pedi_vend),
        movi_hora=timezone.now().time()
    )
    
    return movimento

# Integração com contas a receber
def registrar_recebimento_caixa(conta_receber, valor_recebido):
    """Registra recebimento de conta no caixa"""
    
    movimento = Movicaixa.objects.create(
        movi_empr=conta_receber.empresa,
        movi_fili=conta_receber.filial,
        movi_caix=1,
        movi_data=date.today(),
        movi_entr=valor_recebido,
        movi_said=Decimal('0.00'),
        movi_tipo=10,  # Tipo: Recebimento
        movi_obse=f'Recebimento - Conta {conta_receber.numero}',
        movi_clie=conta_receber.cliente_id,
        movi_hora=timezone.now().time()
    )
    
    return movimento
```

## Troubleshooting

### Problemas Comuns

1. **Caixa não abre**
   - Verificar se já existe caixa aberto para a data
   - Validar permissões do operador
   - Conferir configuração do ECF

2. **Movimentos rejeitados**
   - Verificar se caixa está aberto
   - Validar valores (não negativos)
   - Conferir sequencial de controle

3. **Saldo inconsistente**
   - Executar conferência de caixa
   - Verificar movimentos duplicados
   - Recalcular totais

4. **Performance lenta em relatórios**
   - Criar índices apropriados
   - Usar agregações no banco
   - Implementar cache para consultas frequentes

5. **Problemas de fechamento**
   - Verificar se todos os movimentos foram registrados
   - Validar saldo antes do fechamento
   - Conferir permissões do operador

### Logs de Debug

```python
# settings.py
LOGGING = {
    'loggers': {
        'CaixaDiario': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### Comandos de Manutenção

```python
# management/commands/conferir_caixas.py
from django.core.management.base import BaseCommand
from CaixaDiario.models import Caixageral, Movicaixa

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--data', type=str, help='Data para conferência (YYYY-MM-DD)')
        parser.add_argument('--empresa', type=int, help='Código da empresa')
        parser.add_argument('--filial', type=int, help='Código da filial')
    
    def handle(self, *args, **options):
        from datetime import datetime
        
        data = datetime.strptime(options['data'], '%Y-%m-%d').date()
        empresa = options['empresa']
        filial = options['filial']
        
        # Conferir todos os caixas da data
        caixas = Caixageral.objects.filter(
            caix_empr=empresa,
            caix_fili=filial,
            caix_data=data
        )
        
        for caixa in caixas:
            conferencia = conferir_saldo_caixa(
                empresa, filial, caixa.caix_caix, data
            )
            
            self.stdout.write(
                f"Caixa {caixa.caix_caix}: Saldo R$ {conferencia['saldo_calculado']}"
            )

# management/commands/fechar_caixas_automatico.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        from datetime import date, timedelta
        
        # Fechar caixas do dia anterior que ficaram abertos
        ontem = date.today() - timedelta(days=1)
        
        caixas_abertos = Caixageral.objects.filter(
            caix_data=ontem,
            caix_aber='S',
            caix_fech_data__isnull=True
        )
        
        for caixa in caixas_abertos:
            # Executar fechamento automático
            # Implementar lógica de fechamento
            pass
        
        self.stdout.write(f'{caixas_abertos.count()} caixas fechados automaticamente')
```