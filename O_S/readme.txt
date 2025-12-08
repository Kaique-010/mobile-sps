CREATE OR REPLACE VIEW os_geral AS (
WITH
pecas_agrupadas AS (
    SELECT
        p.peca_empr,
        p.peca_fili,
        p.peca_os,
        STRING_AGG(pr.prod_nome || ' (R$ ' || p.peca_unit::TEXT || ')', ', ') AS pecas,
        SUM(p.peca_unit * p.peca_quan) AS total_pecas
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
        SUM(s.serv_unit * s.serv_quan) AS total_servicos
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



ALTER TABLE os ADD COLUMN os_assi_clie bytea;
ALTER TABLE os ADD COLUMN os_assi_oper bytea;

CREATE TABLE IF NOT EXISTS os_hora (
  os_hora_empr integer NOT NULL,
  os_hora_fili integer NOT NULL,
  os_hora_os integer NOT NULL,
  os_hora_item integer PRIMARY KEY,
  os_hora_data date NOT NULL,
  os_hora_manh_ini time NULL,
  os_hora_manh_fim time NULL,
  os_hora_tard_ini time NULL,
  os_hora_tard_fim time NULL,
  os_hora_tota numeric(6,2) NULL,
  os_hora_km_sai integer NULL,
  os_hora_km_che integer NULL,
  os_hora_oper integer NULL,
  os_hora_equi varchar(100) NULL,
  os_hora_obse text NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS os_hora_uk ON os_hora (os_hora_empr, os_hora_fili, os_hora_os, os_hora_item);
CREATE INDEX IF NOT EXISTS idx_os_hora_context ON os_hora (os_hora_empr, os_hora_fili, os_hora_os);
