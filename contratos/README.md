# App Contratos

## Visão Geral

O app **contratos** é responsável pela gestão de contratos de vendas da empresa. Este módulo permite criar, controlar e gerenciar contratos comerciais com clientes, incluindo produtos, quantidades,

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

ENDPOINTS DISPONÍVEIS

contratos

GET
/api/{slug}/contratos/contratos-vendas/

POST
/api/{slug}/contratos/contratos-vendas/

GET
/api/{slug}/contratos/contratos-vendas/{cont_cont}/

PUT
/api/{slug}/contratos/contratos-vendas/{cont_cont}/

PATCH
/api/{slug}/contratos/contratos-vendas/{cont_cont}/

DELETE
/api/{slug}/contratos/contratos-vendas/{cont_cont}/
