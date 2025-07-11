# App Parâmetros Admin

O app **Parâmetros Admin** é responsável pelo gerenciamento de módulos, permissões e configurações do sistema. Ele controla quais módulos estão disponíveis para cada empresa/filial e gerencia parâmetros específicos.

## 🎯 Funcionalidades Principais

### 📋 Gestão de Módulos

- Cadastro de todos os módulos do sistema
- Controle de ativação/desativação de módulos
- Ordenação e ícones para interface
- Comando para popular módulos automaticamente

##comandos para criar as tabelas do model

### Modelo de Dados

#### Tabela `modulosmobile`

| Coluna      | Tipo           | Descrição                      |
| ----------- | -------------- | ------------------------------ |
| `modu_codi` | `int`          | Chave primária autoincremental |
| `modu_nome` | `varchar(50)`  | Nome do módulo                 |
| `modu_desc` | `varchar(255)` | Descrição do módulo            |
| `modu_ativ` | `bool`         | Indica se o módulo está ativo  |
| `modu_icon` | `varchar(50)`  | Nome do ícone do módulo        |
| `modu_orde` | `int`          | Ordem de exibição no menu      |

sql para rodar no banco para a criação da tabela

CREATE TABLE IF NOT EXISTS modulosmobile (
modu_codi SERIAL PRIMARY KEY,
modu_nome VARCHAR(50) NOT NULL,
modu_desc VARCHAR(255) NOT NULL,
modu_ativ BOOLEAN NOT NULL,
modu_icon VARCHAR(50) NOT NULL,
modu_orde INT NOT NULL
);

### Comandos em sql para popular inicialmente os modulos

INSERT INTO modulosmobile (modu_nome, modu_desc, modu_ativ, modu_icon, modu_orde)
VALUES
('dashboards', 'Dashboards e relatórios gerenciais', TRUE, 'dashboard', 1),
('dash', 'Dashboard principal', TRUE, 'dashboard', 2),
('Produtos', 'Gestão de produtos e serviços', TRUE, 'inventory', 3),
('Pedidos', 'Gestão de pedidos de venda', TRUE, 'shopping_cart', 4),
('Entradas_Estoque', 'Controle de entradas no estoque', TRUE, 'input', 5),
('Saidas_Estoque', 'Controle de saídas do estoque', TRUE, 'output', 6),
('listacasamento', 'Lista de casamento', TRUE, 'list', 7),
('Entidades', 'Gestão de clientes e fornecedores', TRUE, 'people', 8),
('Orcamentos', 'Gestão de orçamentos', TRUE, 'description', 9),
('contratos', 'Gestão de contratos', TRUE, 'assignment', 10),
('implantacao', 'Gestão de implantações', TRUE, 'build', 11),
('Financeiro', 'Gestão financeira', TRUE, 'account_balance', 12),
('OrdemdeServico', 'Gestão de ordens de serviço', TRUE, 'work', 13),
('O_S', 'Ordens de serviço', TRUE, 'work', 14),
('SpsComissoes', 'Gestão de comissões', TRUE, 'monetization_on', 15),
('OrdemProducao', 'Gestão de ordens de produção', TRUE, 'factory', 16),
('parametros_admin', 'Administração de parâmetros do sistema', TRUE, 'settings', 17),
('CaixaDiario', 'Controle de caixa diário', TRUE, 'account_balance_wallet', 18),
('contas_a_pagar', 'Gestão de contas a pagar', TRUE, 'payment', 19),
('contas_a_receber', 'Gestão de contas a receber', TRUE, 'receipt', 20),
('Gerencial', 'Relatórios gerenciais', TRUE, 'analytics', 21),
('DRE', 'Demonstração do resultado do exercício', TRUE, 'assessment', 22),
('EnvioCobranca', 'Envio de cobrança', TRUE, 'email', 23),
('Sdk_recebimentos', 'SDK de recebimentos', TRUE, 'account_balance', 24),
('auditoria', 'Sistema de auditoria', TRUE, 'security', 25),
('notificacoes', 'Sistema de notificações', TRUE, 'notifications', 26),
('planocontas', 'Plano de contas', TRUE, 'account_tree', 27)

##Tabela PermissaoModulo comando sql para criar a tabela

CREATE TABLE IF NOT EXISTS permissoesmodulosmobile (
perm_codi SERIAL PRIMARY KEY,
perm_empr INT NOT NULL,
perm_fili INT NOT NULL,
perm_modu INT NOT NULL REFERENCES modulosmobile(modu_codi) ON DELETE CASCADE,
perm_ativ BOOLEAN NOT NULL,
perm_usua_libe INT NOT NULL,
perm_data_alte TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

### Comando sql para popular a tabela de permissões

INSERT INTO permissoesmodulosmobile (perm_empr, perm_fili, perm_modu, perm_ativ, perm_usua_libe, perm_data_alte)

SELECT 1 AS perm_empr,
1 AS perm_fili,
modu_codi AS perm_modu,
TRUE AS perm_ativ,
1 AS perm_usua_libe,
NOW() AS perm_data_alte
FROM modulosmobile

