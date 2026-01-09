import os
import psycopg2
import subprocess
import os
import django
from django.core.management import call_command
from decouple import config  


# Conexão com o banco de dados local
LOCAL_DB_NAME = config('LOCAL_DB_NAME')
LOCAL_DB_USER = config('LOCAL_DB_USER')
LOCAL_DB_PASSWORD = config('LOCAL_DB_PASSWORD')
LOCAL_DB_HOST = config('LOCAL_DB_HOST')
LOCAL_DB_PORT = config('LOCAL_DB_PORT')


# SQL para criar tabelas essenciais do Django
SQL_DJANGO_CORE = """
-- Criar tabelas essenciais do Django se não existirem
CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT '',
    UNIQUE(app_label, model)
);

ALTER TABLE django_content_type ADD COLUMN IF NOT EXISTS name VARCHAR(100) NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id),
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
    UNIQUE(group_id, permission_id)
);

CREATE TABLE IF NOT EXISTS auth_user (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_user_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    group_id INTEGER NOT NULL REFERENCES auth_group(id),
    UNIQUE(user_id, group_id)
);

CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id),
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
    UNIQUE(user_id, permission_id)
);

CREATE TABLE IF NOT EXISTS django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE NOT NULL,
    object_id TEXT,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL CHECK (action_flag >= 0),
    change_message TEXT NOT NULL,
    content_type_id INTEGER REFERENCES django_content_type(id),
    user_id INTEGER NOT NULL REFERENCES auth_user(id)
);

CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS django_session_expire_date_a5c62663 ON django_session(expire_date);

CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL
);

--Criação da Tabela para auditoria

CREATE TABLE auditoria_logacao (
id SERIAL PRIMARY KEY,
usuario_id INTEGER REFERENCES usuarios(usua_codi) ON DELETE SET NULL,
data_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
tipo_acao VARCHAR(10) NOT NULL,
url TEXT NOT NULL,
ip INET,
navegador VARCHAR(255) NOT NULL,
dados JSONB,
dados_antes JSONB,
dados_depois JSONB,
campos_alterados JSONB,
objeto_id VARCHAR(100),
modelo VARCHAR(100),
empresa VARCHAR(100),
licenca VARCHAR(100)
);

CREATE INDEX idx_auditoria_empresa_licenca_datahora ON auditoria_logacao (empresa, licenca, data_hora);
CREATE INDEX idx_auditoria_usuario_datahora ON auditoria_logacao (usuario_id, data_hora);
CREATE INDEX idx_auditoria_modelo_objeto ON auditoria_logacao (modelo, objeto_id);
CREATE INDEX idx_auditoria_tipoacao_datahora ON auditoria_logacao (tipo_acao, data_hora);


--criar tabela de onboarding_step_progress se não existir
CREATE TABLE IF NOT EXISTS onboarding_step_progress (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(usua_codi),
    empr_id INTEGER NOT NULL,
    step_slug VARCHAR(50) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(usuario_id, empr_id, step_slug)
);

--cria a tabela cfopweb se não existir
CREATE TABLE IF NOT EXISTS cfopweb (
    cfop_id SERIAL PRIMARY KEY,
    cfop_empr INTEGER NOT NULL,
    cfop_codi VARCHAR(10) NOT NULL UNIQUE,
    cfop_desc VARCHAR(255) NOT NULL,
    cfop_exig_ipi BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_exig_icms BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_exig_pis_cofins BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_exig_cbs BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_exig_ibs BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_gera_st BOOLEAN NOT NULL DEFAULT FALSE,
    cfop_gera_difal BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE cfopweb ADD COLUMN IF NOT EXISTS cfop_exig_pis_cofins BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE cfopweb ADD COLUMN IF NOT EXISTS cfop_exig_cbs BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE cfopweb ADD COLUMN IF NOT EXISTS cfop_exig_ibs BOOLEAN NOT NULL DEFAULT FALSE;

--criar a tabela tabela_icms se não existir
CREATE TABLE IF NOT EXISTS tabela_icms (
    tabe_id SERIAL PRIMARY KEY,
    tabe_empr INTEGER NOT NULL,
    tabe_uf_orig VARCHAR(2) NOT NULL,
    tabe_uf_dest VARCHAR(2) NOT NULL,
    tabe_aliq_interna NUMERIC(5,2) NOT NULL,
    tabe_aliq_inter NUMERIC(5,2) NOT NULL,
    tabe_mva_st NUMERIC(6,2),
    UNIQUE(tabe_empr, tabe_uf_orig, tabe_uf_dest)
);

--criar a tabela ncm_aliquotas_ibpt se não existir
CREATE TABLE IF NOT EXISTS ncm_aliquotas_ibpt (
    nali_id SERIAL PRIMARY KEY,
    nali_empr INTEGER NOT NULL,
    nali_ncm VARCHAR(10) NOT NULL,
    nali_aliq_ipi NUMERIC(6,2) NOT NULL,
    nali_aliq_pis NUMERIC(6,2) NOT NULL,
    nali_aliq_cofins NUMERIC(6,2) NOT NULL,
    nali_aliq_cbs NUMERIC(6,2) NOT NULL,
    nali_aliq_ibs NUMERIC(6,2) NOT NULL,
    UNIQUE(nali_empr, nali_ncm)
);

-- criar a tabela mapa_cfop se não existir
CREATE TABLE IF NOT EXISTS mapa_cfop (
    id SERIAL PRIMARY KEY,
    tipo_oper VARCHAR(30) NOT NULL,
    uf_origem VARCHAR(2) NOT NULL,
    uf_destino VARCHAR(2) NOT NULL,
    cfop_id INTEGER NOT NULL REFERENCES cfopweb(cfop_id),
    UNIQUE(tipo_oper, uf_origem, uf_destino)
);

ALTER TABLE pedidosvenda add column if not exists pedi_tipo_oper VARCHAR(30) NOT NULL DEFAULT 'VENDA';

-- criar a tabela ncm_cfop_dif se não existir
CREATE TABLE IF NOT EXISTS ncm_cfop_dif (
    ncmdif_id SERIAL PRIMARY KEY,
    ncm_id VARCHAR(10) NOT NULL,
    ncm_empr INTEGER NOT NULL,
    cfop_id INTEGER NOT NULL REFERENCES cfopweb(cfop_id),
    ncm_ipi_dif NUMERIC(6,2),
    ncm_pis_dif NUMERIC(6,2),
    ncm_cofins_dif NUMERIC(6,2),
    ncm_cbs_dif NUMERIC(6,2),
    ncm_ibs_dif NUMERIC(6,2),
    ncm_icms_aliq_dif NUMERIC(6,2),
    ncm_st_aliq_dif NUMERIC(6,2),
    UNIQUE(ncm_id, cfop_id)
);

-- Criar tabela modulosmobile se não existir
CREATE TABLE IF NOT EXISTS modulosmobile (
    modu_codi SERIAL PRIMARY KEY,
    modu_nome VARCHAR(100) NOT NULL UNIQUE,
    modu_desc TEXT,
    modu_ativ BOOLEAN NOT NULL DEFAULT TRUE,
    modu_icon VARCHAR(50),
    modu_orde INTEGER
);
 
-- Cria a tabela de parâmetros se não existir
CREATE TABLE IF NOT EXISTS parametrosmobile (
    para_codi SERIAL PRIMARY KEY,
    para_empr INT NOT NULL,
    para_fili INT NOT NULL,
    para_modu_id INT NOT NULL REFERENCES modulosmobile(modu_codi) ON DELETE CASCADE,
    para_nome VARCHAR(100) NOT NULL,
    para_desc TEXT,
    para_valo BOOLEAN NOT NULL DEFAULT FALSE,
    para_ativ BOOLEAN NOT NULL DEFAULT TRUE,
    para_data_alte TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    para_usua_alte INT
);         

--Cria a tabela de itens de visitas
 CREATE TABLE IF NOT EXISTS itensvisita (
    item_id SERIAL PRIMARY KEY,
    item_empr INTEGER NOT NULL,
    item_fili INTEGER NOT NULL,
    item_visita_id INTEGER NOT NULL REFERENCES controlevisita (ctrl_id) ON DELETE CASCADE,
    item_prod VARCHAR(60) NOT NULL,
    item_desc_prod TEXT,
    item_quan NUMERIC(15,5),
    item_unit NUMERIC(15,5),
    item_tota NUMERIC(15,2),
    item_desc NUMERIC(15,2),
    item_unli VARCHAR(10),
    item_data DATE DEFAULT CURRENT_DATE,
    item_obse TEXT,
    item_m2 NUMERIC(15,4),
    item_nome_ambi VARCHAR(100),
    item_queb NUMERIC(5,2) DEFAULT 10,
    item_caix INTEGER,
    item_tipo_calculo VARCHAR(10) DEFAULT 'normal' CHECK (item_tipo_calculo IN ('normal', 'pisos')),
    CONSTRAINT itensvisita_unique UNIQUE (item_empr, item_fili, item_visita_id, item_prod)
);

--Criar a tabela de Auditoria 


--Criação da Tabela para auditoria

CREATE TABLE IF NOT EXISTS auditoria_logacao (
id SERIAL PRIMARY KEY,
usuario_id INTEGER REFERENCES usuarios(usua_codi) ON DELETE SET NULL,
data_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
tipo_acao VARCHAR(10) NOT NULL,
url TEXT NOT NULL,
ip INET,
navegador VARCHAR(255) NOT NULL,
dados JSONB,
dados_antes JSONB,
dados_depois JSONB,
campos_alterados JSONB,
objeto_id VARCHAR(100),
modelo VARCHAR(100),
empresa VARCHAR(100),
licenca VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_auditoria_empresa_licenca_datahora ON auditoria_logacao (empresa, licenca, data_hora);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_datahora ON auditoria_logacao (usuario_id, data_hora);
CREATE INDEX IF NOT EXISTS idx_auditoria_modelo_objeto ON auditoria_logacao (modelo, objeto_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_tipoacao_datahora ON auditoria_logacao (tipo_acao, data_hora);

ALTER TABLE orcamentosvenda ADD COLUMN IF NOT EXISTS pedi_stat VARCHAR(2) NOT NULL DEFAULT '1';
ALTER TABLE pedidosvenda ADD COLUMN IF NOT EXISTS pedi_stat VARCHAR(2) NOT NULL DEFAULT '1';

"""

# SQL de tabelas e inserções
SQL_COMMANDS = """
-- Adiciona colunas
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS usua_senh_mobi VARCHAR(128);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS usua_seto INT;
UPDATE usuarios SET usua_senh_mobi = 'roma3030@' WHERE usua_codi = 1;

-- Cria permissões se não existir
CREATE TABLE IF NOT EXISTS permissoesmodulosmobile (
  perm_codi SERIAL PRIMARY KEY,
  perm_empr INT NOT NULL,
  perm_fili INT NOT NULL,
  perm_modu INT NOT NULL REFERENCES modulosmobile(modu_codi) ON DELETE CASCADE,
  perm_ativ BOOLEAN NOT NULL,
  perm_usua_libe INT NOT NULL,
  perm_data_alte TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- Popula modulos
INSERT INTO modulosmobile (modu_nome, modu_desc, modu_ativ, modu_icon, modu_orde)
SELECT t.modu_nome, t.modu_desc, t.modu_ativ, t.modu_icon, t.modu_orde
FROM (
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
    ('planocontas', 'Plano de contas', TRUE, 'account_tree', 27),
    ('Pisos', 'Rotinas de pisos', TRUE, 'home', 28)
) AS t(modu_nome, modu_desc, modu_ativ, modu_icon, modu_orde)
WHERE NOT EXISTS (
    SELECT 1 FROM modulosmobile m WHERE m.modu_nome = t.modu_nome
);
"""

# Inserir permissões para o usuário 1
SQL_INSERT_PERMISSAO = """
INSERT INTO permissoesmodulosmobile (perm_empr, perm_fili, perm_modu, perm_ativ, perm_usua_libe, perm_data_alte)
SELECT 1 AS perm_empr,
1 AS perm_fili,
modu_codi AS perm_modu,
TRUE AS perm_ativ,
1 AS perm_usua_libe,
NOW() AS perm_data_alte
FROM modulosmobile
WHERE NOT EXISTS (
    SELECT 1 FROM permissoesmodulosmobile p 
    WHERE p.perm_modu = modulosmobile.modu_codi 
    AND p.perm_empr = 1 
    AND p.perm_fili = 1
);
"""

# SQL para parâmetros de controle de lote
SQL_PARAMETROS_LOTE = """
-- Ajustes na tabela de lotes
ALTER TABLE lotesvenda ADD COLUMN IF NOT EXISTS lote_ativ BOOLEAN DEFAULT TRUE;
ALTER TABLE lotesvenda ADD COLUMN IF NOT EXISTS lote_data_fabr DATE;
ALTER TABLE lotesvenda ADD COLUMN IF NOT EXISTS lote_obse TEXT;

-- Parâmetros de controle de lote para produtos
INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 3, 'controla_lote', 'Controla lotes de produtos', false, true, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 3 AND para_nome = 'controla_lote');

INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 3, 'lote_sequencial', 'Gera lotes sequenciais automaticamente', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 3 AND para_nome = 'lote_sequencial');

INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 3, 'obriga_validade', 'Obriga informar data de validade', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 3 AND para_nome = 'obriga_validade');

INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 3, 'dias_vencimento_padrao', 'Dias padrão para vencimento', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 3 AND para_nome = 'dias_vencimento_padrao');

-- Parâmetros de controle de lote para entradas de estoque
INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 5, 'controla_lote_entrada', 'Controla lotes nas entradas de estoque', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 5 AND para_nome = 'controla_lote_entrada');

INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 5, 'obriga_lote_entrada', 'Obriga informar lote nas entradas', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 5 AND para_nome = 'obriga_lote_entrada');

-- Parâmetros de controle de lote para saídas de estoque
INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 6, 'controla_lote_saida', 'Controla lotes nas saídas de estoque', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 6 AND para_nome = 'controla_lote_saida');

INSERT INTO parametrosmobile (para_empr, para_fili, para_modu_id, para_nome, para_desc, para_valo, para_ativ, para_data_alte, para_usua_alte)
SELECT 1, 1, 6, 'obriga_lote_saida', 'Obriga informar lote nas saídas', false, false, CURRENT_TIMESTAMP, 1
WHERE NOT EXISTS (SELECT 1 FROM parametrosmobile WHERE para_empr = 1 AND para_fili = 1 AND para_modu_id = 6 AND para_nome = 'obriga_lote_saida');
"""


# Ajustes de schema para ncm_cfop_dif
SQL_FIX_NCM_CFOP_DIF = """
ALTER TABLE ncm_cfop_dif ADD COLUMN IF NOT EXISTS ncm_empr INTEGER NOT NULL DEFAULT 1;
DO $$
DECLARE r RECORD;
BEGIN
  -- Drop all foreign key constraints on ncm_cfop_dif to avoid type mismatch
  FOR r IN (
    SELECT conname FROM pg_constraint 
    WHERE conrelid = 'ncm_cfop_dif'::regclass AND contype = 'f'
  ) LOOP
    EXECUTE format('ALTER TABLE ncm_cfop_dif DROP CONSTRAINT %I', r.conname);
  END LOOP;
END $$;

ALTER TABLE ncm_cfop_dif ALTER COLUMN ncm_id TYPE VARCHAR(10) USING ncm_id::text;

-- Ensure ncm.ncm_codi is unique for FK reference
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint 
    WHERE conname = 'ncm_codi_unique' AND conrelid = 'ncm'::regclass
  ) THEN
    ALTER TABLE ncm ADD CONSTRAINT ncm_codi_unique UNIQUE (ncm_codi);
  END IF;
END $$;

-- Recreate FK to ncm(ncm_codi)
ALTER TABLE ncm_cfop_dif ADD CONSTRAINT ncm_cfop_dif_ncm_fkey FOREIGN KEY (ncm_id) REFERENCES ncm(ncm_codi);
"""

# SQL de views
SQL_VIEWS = """
-- View produtos_detalhados
CREATE OR REPLACE VIEW public.produtos_detalhados
 AS
 SELECT prod.prod_codi AS codigo,
    prod.prod_nome AS nome,
    prod.prod_unme AS unidade,
    prod.prod_grup AS grupo_id,
    grup.grup_desc AS grupo_nome,
    prod.prod_marc AS marca_id,
    prod.prod_ncm AS ncm,
    marc.marc_nome AS marca_nome,
    tabe.tabe_cuge AS custo,
    tabe.tabe_avis AS preco_vista,
    tabe.tabe_apra AS preco_prazo,
    sald.sapr_sald AS saldo,
    prod.prod_foto AS foto,
    prod.prod_peso_brut AS peso_bruto,
    prod.prod_peso_liqu AS peso_liquido,
    sald.sapr_empr AS empresa,
    sald.sapr_fili AS filial,
    COALESCE(tabe.tabe_cuge, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_estoque,
    COALESCE(tabe.tabe_avis, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_venda_vista,
    COALESCE(tabe.tabe_apra, 0::numeric) * COALESCE(sald.sapr_sald, 0::numeric) AS valor_total_venda_prazo
   FROM produtos prod
     LEFT JOIN gruposprodutos grup ON prod.prod_grup::text = grup.grup_codi::text
     LEFT JOIN marca marc ON prod.prod_marc = marc.marc_codi
     LEFT JOIN tabelaprecos tabe ON prod.prod_codi::text = tabe.tabe_prod::text AND prod.prod_empr = tabe.tabe_empr
     LEFT JOIN saldosprodutos sald ON prod.prod_codi::text = sald.sapr_prod::text;

-- View Pedidos_geral
CREATE OR REPLACE VIEW public.pedidos_geral
 AS
 WITH itens_agrupados AS (
         SELECT i_1.iped_empr,
            i_1.iped_fili,
            i_1.iped_pedi,
            sum(i_1.iped_quan) AS quantidade,
            string_agg(p_1.prod_nome::text, ', '::text ORDER BY i_1.iped_item) AS produtos
           FROM itenspedidovenda i_1
             LEFT JOIN produtos p_1 ON i_1.iped_prod::text = p_1.prod_codi::text AND i_1.iped_empr = p_1.prod_empr
          GROUP BY i_1.iped_empr, i_1.iped_fili, i_1.iped_pedi
        )
 SELECT p.pedi_empr AS empresa,
    p.pedi_fili AS filial,
    p.pedi_nume AS numero_pedido,
    c.enti_clie AS codigo_cliente,
    c.enti_nome AS nome_cliente,
    p.pedi_data AS data_pedido,
    COALESCE(i.quantidade, 0::numeric) AS quantidade_total,
    COALESCE(i.produtos, 'Sem itens'::text) AS itens_do_pedido,
    p.pedi_tota AS valor_total,
        CASE
            WHEN p.pedi_fina = 0 THEN 'À VISTA'::text
            WHEN p.pedi_fina = 1 THEN 'A PRAZO'::text
            WHEN p.pedi_fina = 2 THEN 'SEM FINANCEIRO'::text
            ELSE 'OUTRO'::text
        END AS tipo_financeiro,
    v.enti_nome AS nome_vendedor
   FROM pedidosvenda p
     LEFT JOIN entidades c ON p.pedi_forn = c.enti_clie AND p.pedi_empr = c.enti_empr
     LEFT JOIN entidades v ON p.pedi_vend = v.enti_clie AND p.pedi_empr = v.enti_empr
     LEFT JOIN itens_agrupados i ON p.pedi_nume = i.iped_pedi AND p.pedi_empr = i.iped_empr AND p.pedi_fili = i.iped_fili
  ORDER BY p.pedi_data DESC, p.pedi_nume DESC;

-- View os_geral
CREATE OR REPLACE VIEW public.os_geral
 AS
 WITH pecas_agrupadas AS (
         SELECT p_1.peca_empr,
            p_1.peca_fili,
            p_1.peca_os,
            string_agg(((pr.prod_nome::text || ' (R$ '::text) || p_1.peca_unit::text) || ')'::text, ', '::text) AS pecas,
            sum(p_1.peca_unit * p_1.peca_quan) AS total_pecas
           FROM pecasos p_1
             LEFT JOIN produtos pr ON p_1.peca_prod::text = pr.prod_codi::text AND p_1.peca_empr = pr.prod_empr
          GROUP BY p_1.peca_empr, p_1.peca_fili, p_1.peca_os
        ), servicos_agrupados AS (
         SELECT s_1.serv_empr,
            s_1.serv_fili,
            s_1.serv_os,
            string_agg(((((pr.prod_nome::text || ' x'::text) || s_1.serv_quan) || ' (R$ '::text) || s_1.serv_unit::text) || ')'::text, ', '::text) AS servicos,
            sum(s_1.serv_unit * s_1.serv_quan) AS total_servicos
           FROM servicosos s_1
             LEFT JOIN produtos pr ON s_1.serv_prod::text = pr.prod_codi::text AND s_1.serv_empr = pr.prod_empr
          GROUP BY s_1.serv_empr, s_1.serv_fili, s_1.serv_os
        )
 SELECT os.os_empr AS empresa,
    os.os_fili AS filial,
    os.os_os AS ordem_de_servico,
    os.os_clie AS cliente,
    cli.enti_nome AS nome_cliente,
    os.os_data_aber AS data_abertura,
    os.os_data_fech AS data_fim,
    os.os_situ AS situacao_os,
    COALESCE(p.pecas, 'Sem peças'::text) AS pecas,
    COALESCE(s.servicos, 'Sem serviços'::text) AS servicos,
    COALESCE(p.total_pecas, 0::numeric) + COALESCE(s.total_servicos, 0::numeric) AS total_os,
        CASE os.os_stat_os
            WHEN 0 THEN 'Aberta'::text
            WHEN 1 THEN 'Em Orçamento gerado'::text
            WHEN 2 THEN 'Aguardando Liberação'::text
            WHEN 3 THEN 'Liberada'::text
            WHEN 4 THEN 'Finalizada'::text
            WHEN 5 THEN 'Reprovada'::text
            WHEN 20 THEN 'Faturada parcial'::text
            ELSE 'Desconhecido'::text
        END AS status_os,
    os.os_prof_aber AS responsavel,
    aten.enti_nome AS atendente
   FROM os
     LEFT JOIN pecas_agrupadas p ON p.peca_os = os.os_os AND p.peca_empr = os.os_empr AND p.peca_fili = os.os_fili
     LEFT JOIN servicos_agrupados s ON s.serv_os = os.os_os AND s.serv_empr = os.os_empr AND s.serv_fili = os.os_fili
     LEFT JOIN entidades cli ON os.os_clie = cli.enti_clie AND os.os_empr = cli.enti_empr
     LEFT JOIN entidades aten ON os.os_prof_aber = aten.enti_clie AND os.os_empr = aten.enti_empr
  ORDER BY os.os_data_aber DESC, os.os_os DESC;

-- view para envio de cobrança 

 WITH titulos_abertos AS (
         SELECT t_1.titu_empr,
            t_1.titu_fili,
            t_1.titu_clie,
            t_1.titu_titu,
            t_1.titu_seri,
            t_1.titu_parc,
            t_1.titu_venc,
            t_1.titu_valo,
            t_1.titu_linh_digi,
            t_1.titu_url_bole,
            t_1.titu_form_reci
           FROM titulosreceber t_1
             LEFT JOIN baretitulos b ON b.bare_titu::text = t_1.titu_titu::text AND b.bare_parc::text = t_1.titu_parc::text AND b.bare_seri::text = t_1.titu_seri::text AND b.bare_clie = t_1.titu_clie AND b.bare_empr = t_1.titu_empr
          WHERE t_1.titu_aber::text = 'A'::text AND b.bare_titu IS NULL AND t_1.titu_venc >= '2025-07-01'::date AND t_1.titu_venc <= '2025-07-31'::date
        )
 SELECT t.titu_empr AS empresa,
    t.titu_fili AS filial,
    t.titu_clie AS cliente_id,
    e.enti_nome AS cliente_nome,
    e.enti_celu AS cliente_celular,
    e.enti_fone AS cliente_telefone,
	e.enti_emai AS cliente_email,
    t.titu_titu AS numero_titulo,
    t.titu_seri AS serie,
    t.titu_parc AS parcela,
    t.titu_venc AS vencimento,
    t.titu_valo AS valor,
    t.titu_form_reci AS forma_recebimento_codigo,
        CASE t.titu_form_reci
            WHEN '00'::text THEN 'DUPLICATA'::text
            WHEN '01'::text THEN 'CHEQUE'::text
            WHEN '02'::text THEN 'PROMISSÓRIA'::text
            WHEN '03'::text THEN 'RECIBO'::text
            WHEN '50'::text THEN 'CHEQUE PRÉ'::text
            WHEN '51'::text THEN 'CARTÃO DE CRÉDITO'::text
            WHEN '52'::text THEN 'CARTÃO DE DÉBITO'::text
            WHEN '53'::text THEN 'BOLETO BANCÁRIO'::text
            WHEN '54'::text THEN 'DINHEIRO'::text
            WHEN '55'::text THEN 'DEPÓSITO EM CONTA'::text
            WHEN '56'::text THEN 'VENDA À VISTA'::text
            WHEN '60'::text THEN 'PIX'::text
            ELSE 'OUTRO'::text
        END AS forma_recebimento_nome,
    t.titu_linh_digi AS linha_digitavel,
    t.titu_url_bole AS url_boleto
   FROM titulos_abertos t
     LEFT JOIN entidades e ON e.enti_clie = t.titu_clie AND e.enti_empr = t.titu_empr
  ORDER BY t.titu_venc;

-- View balancete_cc
CREATE OR REPLACE VIEW public.balancete_cc
 AS
 WITH recebimentos AS (
         SELECT baretitulos.bare_empr AS empr,
            baretitulos.bare_fili AS fili,
            baretitulos.bare_cecu::text AS cecu_redu,
            COALESCE(c.cecu_nome, 'SEM CENTRO DE CUSTO'::character varying) AS centro_nome,
            COALESCE(c.cecu_anal, 'SEM'::character varying) AS tipo_cc,
            to_char(baretitulos.bare_dpag::timestamp with time zone, 'MM'::text) AS mes_num,
            date_part('month'::text, baretitulos.bare_dpag) AS mes_ordem,
                CASE date_part('month'::text, baretitulos.bare_dpag)
                    WHEN 1 THEN 'JANEIRO'::text
                    WHEN 2 THEN 'FEVEREIRO'::text
                    WHEN 3 THEN 'MARÇO'::text
                    WHEN 4 THEN 'ABRIL'::text
                    WHEN 5 THEN 'MAIO'::text
                    WHEN 6 THEN 'JUNHO'::text
                    WHEN 7 THEN 'JULHO'::text
                    WHEN 8 THEN 'AGOSTO'::text
                    WHEN 9 THEN 'SETEMBRO'::text
                    WHEN 10 THEN 'OUTUBRO'::text
                    WHEN 11 THEN 'NOVEMBRO'::text
                    WHEN 12 THEN 'DEZEMBRO'::text
                    ELSE 'MÊS_DESCONHECIDO'::text
                END AS mes_nome,
            date_part('year'::text, baretitulos.bare_dpag) AS ano,
            sum(baretitulos.bare_pago) AS valor_recebido
           FROM baretitulos
             LEFT JOIN centrodecustos c ON c.cecu_redu::text = baretitulos.bare_cecu::text
          GROUP BY baretitulos.bare_empr, baretitulos.bare_fili, baretitulos.bare_cecu, c.cecu_nome, c.cecu_anal, (date_part('year'::text, baretitulos.bare_dpag)), (to_char(baretitulos.bare_dpag::timestamp with time zone, 'MM'::text)), (date_part('month'::text, baretitulos.bare_dpag))
        ), pagamentos AS (
         SELECT bapatitulos.bapa_empr AS empr,
            bapatitulos.bapa_fili AS fili,
            bapatitulos.bapa_cecu::text AS cecu_redu,
            COALESCE(c.cecu_nome, 'SEM CENTRO DE CUSTO'::character varying) AS centro_nome,
            COALESCE(c.cecu_anal, 'SEM'::character varying) AS tipo_cc,
            to_char(bapatitulos.bapa_dpag::timestamp with time zone, 'MM'::text) AS mes_num,
            date_part('month'::text, bapatitulos.bapa_dpag) AS mes_ordem,
                CASE date_part('month'::text, bapatitulos.bapa_dpag)
                    WHEN 1 THEN 'JANEIRO'::text
                    WHEN 2 THEN 'FEVEREIRO'::text
                    WHEN 3 THEN 'MARÇO'::text
                    WHEN 4 THEN 'ABRIL'::text
                    WHEN 5 THEN 'MAIO'::text
                    WHEN 6 THEN 'JUNHO'::text
                    WHEN 7 THEN 'JULHO'::text
                    WHEN 8 THEN 'AGOSTO'::text
                    WHEN 9 THEN 'SETEMBRO'::text
                    WHEN 10 THEN 'OUTUBRO'::text
                    WHEN 11 THEN 'NOVEMBRO'::text
                    WHEN 12 THEN 'DEZEMBRO'::text
                    ELSE 'MÊS_DESCONHECIDO'::text
                END AS mes_nome,
            date_part('year'::text, bapatitulos.bapa_dpag) AS ano,
            sum(bapatitulos.bapa_pago) AS valor_pago
           FROM bapatitulos
             LEFT JOIN centrodecustos c ON c.cecu_redu::text = bapatitulos.bapa_cecu::text
          GROUP BY bapatitulos.bapa_empr, bapatitulos.bapa_fili, bapatitulos.bapa_cecu, c.cecu_nome, c.cecu_anal, (date_part('year'::text, bapatitulos.bapa_dpag)), (to_char(bapatitulos.bapa_dpag::timestamp with time zone, 'MM'::text)), (date_part('month'::text, bapatitulos.bapa_dpag))
        )
 SELECT COALESCE(r.empr, p.empr) AS empr,
    COALESCE(r.fili, p.fili) AS fili,
    COALESCE(r.cecu_redu, p.cecu_redu) AS cecu_redu,
    COALESCE(r.centro_nome, p.centro_nome) AS centro_nome,
    COALESCE(r.tipo_cc, p.tipo_cc) AS tipo_cc,
    COALESCE(r.mes_num, p.mes_num) AS mes_num,
    COALESCE(r.mes_nome, p.mes_nome) AS mes_nome,
    COALESCE(r.ano, p.ano) AS ano,
    COALESCE(r.mes_ordem, p.mes_ordem) AS mes_ordem,
    COALESCE(r.valor_recebido, 0::numeric) AS valor_recebido,
    COALESCE(p.valor_pago, 0::numeric) AS valor_pago,
    COALESCE(r.valor_recebido, 0::numeric) - COALESCE(p.valor_pago, 0::numeric) AS resultado
   FROM recebimentos r
     FULL JOIN pagamentos p ON r.cecu_redu = p.cecu_redu AND r.mes_num = p.mes_num AND r.empr = p.empr AND r.fili = p.fili
  ORDER BY (COALESCE(r.mes_ordem, p.mes_ordem));

-- view para envio de cobrança 
CREATE OR REPLACE VIEW public.enviarcobranca
 AS
 WITH titulos_abertos AS (
         SELECT t_1.titu_empr,
            t_1.titu_fili,
            t_1.titu_clie,
            t_1.titu_titu,
            t_1.titu_seri,
            t_1.titu_parc,
            t_1.titu_venc,
            t_1.titu_valo,
            t_1.titu_bole, 
            t_1.titu_form_reci
           FROM titulosreceber t_1
             LEFT JOIN baretitulos b ON b.bare_titu::text = t_1.titu_titu::text AND b.bare_parc::text = t_1.titu_parc::text AND b.bare_seri::text = t_1.titu_seri::text AND b.bare_clie = t_1.titu_clie AND b.bare_empr = t_1.titu_empr
          WHERE t_1.titu_aber::text = 'A'::text AND b.bare_titu IS NULL AND t_1.titu_venc >= '2023-07-01'::date AND t_1.titu_venc <= '2026-07-31'::date
        )
 SELECT t.titu_empr AS empresa,
    t.titu_fili AS filial,
    t.titu_clie AS cliente_id,
    e.enti_nome AS cliente_nome,
    e.enti_celu AS cliente_celular,
    e.enti_fone AS cliente_telefone,
	  e.enti_emai AS cliente_email,
    t.titu_titu AS numero_titulo,
    t.titu_seri AS serie,
    t.titu_parc AS parcela,
    t.titu_venc AS vencimento,
    t.titu_valo AS valor,
    t.titu_bole AS boleto,
    t.titu_form_reci AS forma_recebimento_codigo,
        CASE t.titu_form_reci
            WHEN '00'::text THEN 'DUPLICATA'::text
            WHEN '01'::text THEN 'CHEQUE'::text
            WHEN '02'::text THEN 'PROMISSÓRIA'::text
            WHEN '03'::text THEN 'RECIBO'::text
            WHEN '50'::text THEN 'CHEQUE PRÉ'::text
            WHEN '51'::text THEN 'CARTÃO DE CRÉDITO'::text
            WHEN '52'::text THEN 'CARTÃO DE DÉBITO'::text
            WHEN '53'::text THEN 'BOLETO BANCÁRIO'::text
            WHEN '54'::text THEN 'DINHEIRO'::text
            WHEN '55'::text THEN 'DEPÓSITO EM CONTA'::text
            WHEN '56'::text THEN 'VENDA À VISTA'::text
            WHEN '60'::text THEN 'PIX'::text
            ELSE 'OUTRO'::text
        END AS forma_recebimento_nome,
    t.titu_bole AS url_boleto
   FROM titulos_abertos t
     LEFT JOIN entidades e ON e.enti_clie = t.titu_clie AND e.enti_empr = t.titu_empr
  ORDER BY t.titu_venc;

--view aniversariantes
CREATE OR REPLACE VIEW public.aniversariantes
 AS
 WITH dados_validos AS (
                    SELECT 
                        DISTINCT enti_empr, 
                        enti_clie AS codigo,
                        enti_nome AS nome,
                        enti_tipo_enti AS tipo,
                        enti_dana,
                        CASE 
                            WHEN enti_dana IS NOT NULL AND EXTRACT(YEAR FROM enti_dana) BETWEEN 1900 AND 2100 
                            THEN TO_CHAR(enti_dana, 'DD/MM') 
                            ELSE 'Data inválida' 
                        END AS aniversario,
                        CASE 
                            WHEN enti_dana IS NOT NULL AND EXTRACT(YEAR FROM enti_dana) BETWEEN 1900 AND 2100 
                            THEN EXTRACT(MONTH FROM enti_dana)
                            ELSE 99 
                        END AS mes_nascimento,
                        CASE 
                            WHEN enti_dana IS NOT NULL AND EXTRACT(YEAR FROM enti_dana) BETWEEN 1900 AND 2100 
                            THEN EXTRACT(DAY FROM enti_dana)    
                            ELSE 99
                        END AS dia_nascimento,
                        COALESCE(enti_fone, enti_celu, 'Sem telefone') AS contato,
                        enti_emai AS email
                    FROM entidades
                    WHERE enti_dana IS NOT NULL
                    AND EXTRACT(YEAR FROM enti_dana) BETWEEN 1900 AND 2100
                ),
                aniversarios_validos AS (
                    SELECT *,
                        MAKE_DATE(EXTRACT(YEAR FROM CURRENT_DATE)::int, 
                                    mes_nascimento::int, 
                                    dia_nascimento::int) AS aniversario_deste_ano
                    FROM dados_validos
                    WHERE
                    enti_empr = 1 AND
                    mes_nascimento BETWEEN 1 AND 12
                    AND dia_nascimento BETWEEN 1 AND 31
                    -- Filtra combinações impossíveis
                    AND (mes_nascimento, dia_nascimento) NOT IN ((2,30), (2,31), (4,31), (6,31), (9,31), (11,31))
                    -- Exclui 29/02 em ano não bissexto
                    AND NOT (
                        mes_nascimento = 2 AND dia_nascimento = 29 AND
                        NOT (
                            (EXTRACT(YEAR FROM CURRENT_DATE)::int % 4 = 0 AND EXTRACT(YEAR FROM CURRENT_DATE)::int % 100 != 0)
                            OR (EXTRACT(YEAR FROM CURRENT_DATE)::int % 400 = 0)
                        )
                    )
                )
                SELECT 
                    enti_empr, codigo,  nome, tipo, aniversario, mes_nascimento, dia_nascimento, contato, email
                FROM aniversarios_validos
                ORDER BY aniversario_deste_ano;


-- View extrato_caixa
CREATE OR REPLACE VIEW public.extrato_caixa
 AS(
 SELECT x.iped_pedi AS "Pedido",
    x.pedi_forn AS "Cliente",
    x.enti_nome AS "Nome Cliente",
    x.iped_prod AS "Produto",
    x.prod_nome AS "Descrição",
    x.iped_quan AS "Quantidade",
    sum(x.iped_tota) / (( SELECT count(DISTINCT movicaixa.movi_tipo) AS count
           FROM movicaixa
          WHERE x.iped_pedi = movicaixa.movi_nume_vend AND x.iped_empr = movicaixa.movi_empr AND x.iped_fili = movicaixa.movi_fili))::numeric AS "Valor Total",
    x.movi_data AS "Data",
    x."Forma de Recebimento",
    x.iped_empr AS "Empresa",
    x.iped_fili AS "Filial"
   FROM ( SELECT DISTINCT i.iped_empr,
            i.iped_fili,
            i.iped_pedi,
            i.iped_prod,
            i.iped_quan,
            p.pedi_forn,
            e.enti_nome,
            prod.prod_nome,
            i.iped_tota,
            m.movi_data,
                CASE
                    WHEN m.movi_tipo = 1 THEN 'DINHEIRO'::text
                    WHEN m.movi_tipo = 2 THEN 'CHEQUE'::text
                    WHEN m.movi_tipo = 3 THEN 'CARTAO CREDITO'::text
                    WHEN m.movi_tipo = 4 THEN 'CARTAO DEBITO'::text
                    WHEN m.movi_tipo = 5 THEN 'CREDIARIO'::text
                    WHEN m.movi_tipo = 6 THEN 'PIX'::text
                    ELSE 'OUTRO'::text
                END AS "Forma de Recebimento"
           FROM itenspedidovenda i
             JOIN movicaixa m ON i.iped_pedi = m.movi_nume_vend AND i.iped_empr = m.movi_empr AND i.iped_fili = m.movi_fili
             JOIN produtos prod ON prod.prod_empr = i.iped_empr AND prod.prod_codi::text = i.iped_prod::text
             JOIN pedidosvenda p ON p.pedi_nume = i.iped_pedi AND p.pedi_empr = i.iped_empr AND p.pedi_fili = i.iped_fili
             JOIN entidades e ON e.enti_clie = p.pedi_forn AND e.enti_empr = p.pedi_empr
          WHERE m.movi_data >= '2020-01-01'::date AND m.movi_data <= '2025-12-31'::date AND m.movi_nume_vend > 0 AND i.iped_empr = 1 AND i.iped_fili = 1) x
  GROUP BY x.pedi_forn, x.enti_nome, x."Forma de Recebimento", x.iped_empr, x.iped_fili, x.iped_pedi, x.iped_prod, x.prod_nome, x.movi_data, x.iped_quan
  ORDER BY x.iped_pedi);
"""

# Tabelas do módulo Notas Fiscais (NF-e)
SQL_NOTAS_FISCAIS = """
-- nf_nota (cabeçalho da nota)
CREATE TABLE IF NOT EXISTS nf_nota (
    id SERIAL PRIMARY KEY,
    empresa INTEGER NOT NULL,
    filial INTEGER NOT NULL,
    modelo VARCHAR(2) NOT NULL DEFAULT '55',
    serie VARCHAR(3) NOT NULL,
    numero INTEGER NOT NULL,
    data_emissao DATE NOT NULL DEFAULT CURRENT_DATE,
    data_saida DATE,
    tipo_operacao INTEGER NOT NULL,
    finalidade INTEGER NOT NULL DEFAULT 1,
    ambiente INTEGER NOT NULL DEFAULT 2,
    emitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    status INTEGER NOT NULL DEFAULT 0,
    chave_acesso VARCHAR(50),
    protocolo_autorizacao VARCHAR(60),
    xml_assinado TEXT,
    xml_autorizado TEXT,
    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT nf_nota_unique UNIQUE (empresa, filial, modelo, serie, numero)
);

-- nf_nota_item (itens da nota)
CREATE TABLE IF NOT EXISTS nf_nota_item (
    id SERIAL PRIMARY KEY,
    nota_id INTEGER NOT NULL REFERENCES nf_nota(id) ON DELETE CASCADE,
    produto_id VARCHAR(50) NOT NULL,
    quantidade NUMERIC(15,4) NOT NULL,
    unitario NUMERIC(15,4) NOT NULL,
    desconto NUMERIC(15,4) NOT NULL DEFAULT 0,
    cfop VARCHAR(4) NOT NULL,
    ncm VARCHAR(8) NOT NULL,
    cest VARCHAR(7),
    cst_icms VARCHAR(3) NOT NULL,
    cst_pis VARCHAR(2) NOT NULL,
    cst_cofins VARCHAR(2) NOT NULL,
    total NUMERIC(15,2) NOT NULL,
    CONSTRAINT idx_nf_item_nota_id UNIQUE (id)
);
CREATE INDEX IF NOT EXISTS ix_nf_nota_item_nota ON nf_nota_item(nota_id);
CREATE INDEX IF NOT EXISTS ix_nf_nota_item_produto ON nf_nota_item(produto_id);

-- nf_item_imposto (impostos por item)
CREATE TABLE IF NOT EXISTS nf_item_imposto (
    id SERIAL PRIMARY KEY,
    item_id INTEGER UNIQUE NOT NULL REFERENCES nf_nota_item(id) ON DELETE CASCADE,
    icms_base NUMERIC(15,2),
    icms_valor NUMERIC(15,2),
    icms_aliquota NUMERIC(5,2),
    ipi_valor NUMERIC(15,2),
    pis_valor NUMERIC(15,2),
    cofins_valor NUMERIC(15,2),
    fcp_valor NUMERIC(15,2),
    ibs_base NUMERIC(15,2),
    ibs_aliquota NUMERIC(5,2),
    ibs_valor NUMERIC(15,2),
    cbs_base NUMERIC(15,2),
    cbs_aliquota NUMERIC(5,2),
    cbs_valor NUMERIC(15,2)
);
CREATE INDEX IF NOT EXISTS ix_nf_item_imposto_item ON nf_item_imposto(item_id);

-- nf_transporte (dados de frete)
CREATE TABLE IF NOT EXISTS nf_transporte (
    id SERIAL PRIMARY KEY,
    nota_id INTEGER UNIQUE NOT NULL REFERENCES nf_nota(id) ON DELETE CASCADE,
    modalidade_frete INTEGER NOT NULL,
    transportadora_id INTEGER,
    placa_veiculo VARCHAR(8),
    uf_veiculo VARCHAR(2)
);
CREATE INDEX IF NOT EXISTS ix_nf_transporte_nota ON nf_transporte(nota_id);

-- nf_nota_evento (eventos da nota)
CREATE TABLE IF NOT EXISTS nf_nota_evento (
    id SERIAL PRIMARY KEY,
    nota_id INTEGER NOT NULL REFERENCES nf_nota(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL,
    descricao TEXT NOT NULL,
    xml TEXT,
    protocolo VARCHAR(60),
    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_nf_evento_nota_tipo ON nf_nota_evento(nota_id, tipo);
"""

def executar_sql(sql, titulo="SQL", ignore_errors=False):
    print(f"🚀 Executando: {titulo}")
    conn = psycopg2.connect(
        dbname=LOCAL_DB_NAME,
        user=LOCAL_DB_USER,
        password=LOCAL_DB_PASSWORD,
        host=LOCAL_DB_HOST,
        port=LOCAL_DB_PORT
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for stmt in statements:
                try:
                    cur.execute(stmt + ';')
                except Exception as e:
                    if not ignore_errors:
                        raise
                    print(f"⚠️ Falha ao executar statement, continuando: {e}\nSQL: {stmt[:200]}...")
    finally:
        conn.close()
    print(f"✅ {titulo} executado.\n")

def rodar_comando(cmd, ignore_errors=False):
    print(f"⚙️ Rodando comando: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("✅ Comando executado.\n")
    except subprocess.CalledProcessError as e:
        if ignore_errors:
            print(f"⚠️ Comando falhou mas continuando: {e}\n")
        else:
            raise e
    

def main():
    os.environ['DISABLE_AUDIT_SIGNALS'] = '1'
    os.environ['DISABLE_PARAM_ADMIN_READY'] = '1'
    if not django.apps.apps.ready:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
    print("🔧 Criando tabelas essenciais do Django...")
    executar_sql(SQL_DJANGO_CORE, "Criação de tabelas essenciais do Django", ignore_errors=True)
    
    print("📦 Aplicando migrações respeitando dependências (user model customizado)...")
    # Com AUTH_USER_MODEL = 'Licencas.Usuarios', o app admin depende de Licencas.
    # Usamos --fake-initial para marcar as iniciais quando as tabelas já existem pelo SQL, mas
    # garantimos que Licencas rode antes para evitar InconsistentMigrationHistory.
    try:
        call_command('migrate', 'contenttypes', '0001', fake=True, interactive=False, verbosity=0)
        call_command('migrate', 'contenttypes', '0002', fake=True, interactive=False, verbosity=0)
        call_command('migrate', 'Licencas', fake_initial=True, interactive=False, verbosity=0)
        call_command('migrate', fake_initial=True, interactive=False, verbosity=0)
    except Exception as e:
        print(f"⚠️ Migração inicial com call_command falhou, continuando com subprocess: {e}")
        rodar_comando("python manage.py migrate contenttypes 0001 --fake --noinput --verbosity 0", ignore_errors=True)
        rodar_comando("python manage.py migrate contenttypes 0002 --fake --noinput --verbosity 0", ignore_errors=True)
        rodar_comando("python manage.py migrate Licencas --fake-initial --noinput --verbosity 0", ignore_errors=True)
        rodar_comando("python manage.py migrate --fake-initial --noinput --verbosity 0", ignore_errors=True)
    # Migração consolidada sem varrer app a app (mais leve)
    try:
        call_command('migrate', fake_initial=True, interactive=False, verbosity=0)
    except Exception as e:
        print(f"⚠️ Migração consolidada falhou, usando subprocess: {e}")
        rodar_comando("python manage.py migrate --fake-initial --noinput --verbosity 0", ignore_errors=True)
    
    print("📦 Executando SQL customizado...")
    executar_sql(SQL_COMMANDS, "Criação e atualização de tabelas", ignore_errors=True)
    executar_sql(SQL_INSERT_PERMISSAO, "Inserção de permissões para usuário 1", ignore_errors=True)
    executar_sql(SQL_PARAMETROS_LOTE, "Inserção de parâmetros de controle de lote", ignore_errors=True)
    executar_sql(SQL_NOTAS_FISCAIS, "Criação de tabelas Notas Fiscais (NF-e)", ignore_errors=True)
    executar_sql(SQL_FIX_NCM_CFOP_DIF, "Ajustes de schema ncm_cfop_dif", ignore_errors=True)
    try:
        executar_sql(SQL_VIEWS, "Criação de views")
    except Exception as e:
        print(f"⚠️ Falha ao criar views, continuando setup: {e}\n")

    print("📊 Populando parâmetros iniciais...")
    try:
        call_command('populate_parametros', empresa='1', filial='1', verbosity=0)
    except Exception as e:
        print(f"⚠️ Comando populate_parametros via call_command falhou, usando subprocess: {e}")
        rodar_comando("python manage.py populate_parametros --empresa 1 --filial 1")

    print("📦 Rodando migrações do app onboarding...")
    try:
        call_command('migrate', 'onboarding', fake_initial=True, interactive=False, verbosity=0)
    except Exception as e:
        print(f"⚠️ Migração do app onboarding via call_command falhou, usando subprocess: {e}")
        rodar_comando("python manage.py migrate onboarding --fake-initial", ignore_errors=True)

    print("🎉 Setup do banco finalizado com sucesso.")


if __name__ == "__main__":
    main()
