import os
import psycopg2
import subprocess
from decouple import config  


# Conexão com o banco de dados local
LOCAL_DB_NAME = config('LOCAL_DB_NAME')
LOCAL_DB_USER = config('LOCAL_DB_USER')
LOCAL_DB_PASSWORD = config('LOCAL_DB_PASSWORD')
LOCAL_DB_HOST = config('LOCAL_DB_HOST')
LOCAL_DB_PORT = config('LOCAL_DB_PORT')



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
SELECT * FROM (VALUES
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
    os.os_vend AS vendedor,
    vend.enti_nome AS nome_vendedor,
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
     LEFT JOIN entidades vend ON os.os_vend = vend.enti_clie AND os.os_empr = vend.enti_empr
  ORDER BY os.os_data_aber DESC, os.os_os DESC;

-- View enviarcobranca
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


-- View extrato_caixa
CREATE OR REPLACE VIEW public.extrato_caixa
 AS
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
  ORDER BY x.iped_pedi;
"""

def executar_sql(sql, titulo="SQL"):
    print(f"🚀 Executando: {titulo}")
    conn = psycopg2.connect(
        dbname=LOCAL_DB_NAME,
        user=LOCAL_DB_USER,
        password=LOCAL_DB_PASSWORD,
        host=LOCAL_DB_HOST,
        port=LOCAL_DB_PORT
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print(f"✅ {titulo} executado com sucesso.\n")

def rodar_comando(cmd):
    print(f"⚙️ Rodando comando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)
    print("✅ Comando executado.\n")

def main():
    print("📦 Aplicando migrations...")
    rodar_comando("python manage.py migrate parametros_admin  --fake-initial")
    rodar_comando("python manage.py migrate notificacoes  --fake-initial")
    rodar_comando("python manage.py migrate auditoria  --fake-initial")
    rodar_comando("python manage.py migrate SpsComissoes  --fake-initial")
    rodar_comando("python manage.py migrate Sdk_recebimentos  --fake-initial")

    executar_sql(SQL_COMMANDS, "Criação e atualização de tabelas")
    executar_sql(SQL_INSERT_PERMISSAO, "Inserção de permissões para usuário 1")
    executar_sql(SQL_VIEWS, "Criação de views")

    print("📊 Populando parâmetros iniciais...")
    rodar_comando("python manage.py populate_parametros --empresa 1 --filial 1")

    print("🎉 Setup do banco finalizado com sucesso.")


if __name__ == "__main__":
    main()