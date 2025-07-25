Comandos em Bases novas para rodar o Mobile:

Alterar o .env pra que o default seja o banco que esta migrando e adicionar usuario e senha do banco no .env

--alterar a tabela de usuarios com usua_senh_mobi e com usua_seto
ALTER TABLE usuarios ADD COLUMN usua_senh_mobi VARCHAR(128);
ALTER TABLE usuarios ADD COLUMN usua_seto INT;
UPDATE usuarios SET usua_senh_mobi = 'roma3030@' WHERE usua_codi = 1;

Rodar as migrates para criar as tabelas dos apps novos com:
python manage.py migrate parametros_admin e notificações
python manage.py migrate auditoria
python manage.py migrate notificações
python manage.py migrate SpsComissoes
python manage.py migrate Sdk_recebimentos

Depois popular com os modulos

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

--popular os parametros do sistema com:
python manage.py populate_parametros --empresa 1 --filial 1

--Roda o projeto pra teste
python manage.py runserver 0.0.0.0:8000

--Rodar as tabelas novas que são de managed False

-- Balançete por Centro de Custo
-- By: Leonardo Sousa

-- Criação da View Balançete por Centro de Custo

create or REPLACE view balancete_cc as(
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
ORDER BY (COALESCE(r.mes_ordem, p.mes_ordem)))

CREATE OR REPLACE VIEW os_geral AS (
WITH
pecas_agrupadas AS (
SELECT
p.peca_empr,
p.peca_fili,
p.peca_os,
STRING_AGG(pr.prod_nome || ' (R$ ' || p.peca_unit::TEXT || ')', ', ') AS pecas,
SUM(p.peca_unit \* p.peca_quan) AS total_pecas
FROM pecasos p
LEFT JOIN produtos pr
ON p.peca_prod = pr.prod_codi
AND p.peca_empr = pr.prod_empr
GROUP BY p.peca_empr, p.peca_fili, p.peca_os
),

servicos_agrupados AS (
SELECT
s.serv_empr,
s.serv_fili,
s.serv_os,
STRING_AGG(pr.prod_nome || ' x' || s.serv_quan || ' (R$ ' || s.serv_unit::TEXT || ')', ', ') AS servicos,
SUM(s.serv_unit \* s.serv_quan) AS total_servicos
FROM servicosos s
LEFT JOIN produtos pr
ON s.serv_prod = pr.prod_codi
AND s.serv_empr = pr.prod_empr
GROUP BY s.serv_empr, s.serv_fili, s.serv_os
)

SELECT
os.os_empr AS empresa,
os.os_fili AS filial,
os.os_os AS ordem_de_servico,
os.os_clie AS cliente,
cli.enti_nome AS nome_cliente,
os.os_data_aber AS data_abertura,
os.os_data_fech AS data_fim,
os.os_situ AS situacao_os,
os.os_vend AS vendedor,
vend.enti_nome AS nome_vendedor,
COALESCE(p.pecas, 'Sem peças') AS pecas,
COALESCE(s.servicos, 'Sem serviços') AS servicos,
COALESCE(p.total_pecas, 0) + COALESCE(s.total_servicos, 0) AS total_os,
CASE os.os_stat_os
WHEN 0 THEN 'Aberta'
WHEN 1 THEN 'Em Orçamento gerado'
WHEN 2 THEN 'Aguardando Liberação'
WHEN 3 THEN 'Liberada'
WHEN 4 THEN 'Finalizada'
WHEN 5 THEN 'Reprovada'
WHEN 20 THEN 'Faturada parcial'
ELSE 'Desconhecido'
END AS status_os,
os.os_prof_aber AS responsavel,
aten.enti_nome AS atendente

FROM os
LEFT JOIN pecas_agrupadas p
ON p.peca_os = os.os_os
AND p.peca_empr = os.os_empr
AND p.peca_fili = os.os_fili
LEFT JOIN servicos_agrupados s
ON s.serv_os = os.os_os
AND s.serv_empr = os.os_empr
AND s.serv_fili = os.os_fili
LEFT JOIN entidades cli
ON os.os_clie = cli.enti_clie AND os.os_empr = cli.enti_empr
LEFT JOIN entidades aten
ON os.os_prof_aber = aten.enti_clie AND os.os_empr = aten.enti_empr
LEFT JOIN entidades vend
ON os.os_vend = vend.enti_clie AND os.os_empr = vend.enti_empr

ORDER BY os.os_data_aber DESC, os.os_os DESC
);

rodar o setup_mobile.py
