# Sistema de Parâmetros Administrativos

## Visão Geral

O sistema de parâmetros administrativos é uma solução completa para gerenciar configurações, permissões e parâmetros específicos por empresa/filial no sistema SPS. Ele oferece controle granular sobre módulos, rotas, configurações de estoque e financeiro.

## Funcionalidades Principais

### 1. Parâmetros Gerais

- Configurações customizáveis por empresa/filial
- Valores tipados (string, integer, float, boolean, json)
- Cache inteligente para performance
- Auditoria completa de alterações

### 2. Permissões de Módulos

- Controle de acesso a módulos específicos
- Integração com sistema de licenças existente
- Permissões por usuário ou grupo
- Cache de permissões para otimização

### 3. Permissões de Rotas

- Controle granular de acesso a endpoints específicos
- Suporte a métodos HTTP (GET, POST, PUT, DELETE)
- Permissões condicionais baseadas em contexto
- Integração com middleware de autenticação

### 4. Configurações de Estoque

- Controle de movimentação de estoque
- Permissões para baixa automática
- Configurações de desconto
- Validações customizadas

### 5. Configurações Financeiras

- Parâmetros de cobrança
- Configurações de pagamento
- Limites e validações financeiras
- Integração com módulos financeiros

## Arquitetura do Sistema

### Modelos de Dados

#### ParametrosGerais

```python

CREATE TABLE param_geral_mobile (
    para_codi SERIAL PRIMARY KEY,
    para_empr INTEGER NOT NULL,
    para_fili INTEGER NOT NULL,
    para_nome VARCHAR(100) NOT NULL,
    para_valo TEXT NOT NULL,
    para_desc TEXT,
    para_tipo VARCHAR(20) DEFAULT 'string',
    para_ativ BOOLEAN DEFAULT TRUE,
    para_data_cria TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    para_data_alte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    para_usua_alte VARCHAR(150),
    UNIQUE (para_empr, para_fili, para_nome)
);

CREATE TABLE perm_modulo_mobile (
    perm_codi SERIAL PRIMARY KEY,
    perm_empr INTEGER NOT NULL,
    perm_fili INTEGER NOT NULL,
    perm_modu VARCHAR(50) NOT NULL,
    perm_ativ BOOLEAN DEFAULT TRUE,
    perm_data_libe TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    perm_data_venc TIMESTAMP,
    perm_usua_libe VARCHAR(150),
    perm_obse TEXT,
    UNIQUE (perm_empr, perm_fili, perm_modu)
);

CREATE TABLE perm_rota_mobile (
    rota_codi SERIAL PRIMARY KEY,
    rota_empr INTEGER NOT NULL,
    rota_fili INTEGER NOT NULL,
    rota_modu VARCHAR(50) NOT NULL,
    rota_nome VARCHAR(100) NOT NULL,
    rota_path VARCHAR(200) NOT NULL,
    rota_tipo VARCHAR(20) DEFAULT 'read',
    rota_ativ BOOLEAN DEFAULT TRUE,
    rota_data_cria TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rota_usua_cria VARCHAR(150),
    UNIQUE (rota_empr, rota_fili, rota_modu, rota_nome)
);

CREATE TABLE conf_estoque_mobile (
    conf_codi SERIAL PRIMARY KEY,
    conf_empr INTEGER NOT NULL,
    conf_fili INTEGER NOT NULL,

    conf_pedi_move_esto BOOLEAN DEFAULT TRUE,
    conf_orca_move_esto BOOLEAN DEFAULT FALSE,
    conf_os_move_esto   BOOLEAN DEFAULT TRUE,
    conf_prod_move_esto BOOLEAN DEFAULT TRUE,

    conf_esto_nega BOOLEAN DEFAULT FALSE,
    conf_esto_mini BOOLEAN DEFAULT TRUE,
    conf_esto_maxi BOOLEAN DEFAULT FALSE,

    conf_custo_medio BOOLEAN DEFAULT TRUE,
    conf_custo_ulti  BOOLEAN DEFAULT FALSE,

    conf_data_alte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conf_usua_alte VARCHAR(150),
    UNIQUE (conf_empr, conf_fili)
);

CREATE TABLE conf_financeiro_mobile (
    conf_codi SERIAL PRIMARY KEY,
    conf_empr INTEGER NOT NULL,
    conf_fili INTEGER NOT NULL,

    conf_perm_desc_pedi BOOLEAN DEFAULT TRUE,
    conf_desc_maxi_pedi DECIMAL(5, 2) DEFAULT 0,
    conf_perm_acre_pedi BOOLEAN DEFAULT TRUE,

    conf_calc_comi_auto BOOLEAN DEFAULT TRUE,
    conf_comi_sobr_desc BOOLEAN DEFAULT FALSE,

    conf_praz_maxi_vend INTEGER DEFAULT 0,
    conf_perm_vend_praz BOOLEAN DEFAULT TRUE,

    conf_data_alte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conf_usua_alte VARCHAR(150),
    UNIQUE (conf_empr, conf_fili)
);

CREATE TABLE log_parametro_mobile (
    log_codi SERIAL PRIMARY KEY,
    log_tabe VARCHAR(50) NOT NULL,
    log_regi INTEGER NOT NULL,
    log_acao VARCHAR(20) NOT NULL,
    log_valo_ante TEXT,
    log_valo_novo TEXT,
    log_usua VARCHAR(150) NOT NULL,
    log_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_ip INET
);
```
