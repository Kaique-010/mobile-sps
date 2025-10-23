
APP PARA MOSTRAGEM DE DASHBOARDS EM GERAL 


ENDPOINT DISPONIVEIS 
dashboards


GET
/api/{slug}/dashboards/balancete-cc/



POST
/api/{slug}/dashboards/balancete-cc/



GET
/api/{slug}/dashboards/balancete-cc/{id}/



PUT
/api/{slug}/dashboards/balancete-cc/{id}/



PATCH
/api/{slug}/dashboards/balancete-cc/{id}/



DELETE
/api/{slug}/dashboards/balancete-cc/{id}/



GET
/api/{slug}/dashboards/dashboard/



POST
/api/{slug}/dashboards/envio/email/



POST
/api/{slug}/dashboards/envio/whatsapp/



GET
/api/{slug}/dashboards/estoque/



GET
/api/{slug}/dashboards/extrato-caixa/



POST
/api/{slug}/dashboards/extrato-caixa/



GET
/api/{slug}/dashboards/extrato-caixa/{id}/



PUT
/api/{slug}/dashboards/extrato-caixa/{id}/



PATCH
/api/{slug}/dashboards/extrato-caixa/{id}/



DELETE
/api/{slug}/dashboards/extrato-caixa/{id}/



GET
/api/{slug}/dashboards/extrato-caixa/resumo/



GET
/api/{slug}/dashboards/financeiro/



GET
/api/{slug}/dashboards/orcamento-analitico/



GET
/api/{slug}/dashboards/orcamento-analitico/{id}/



GET
/api/{slug}/dashboards/vendas/


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



  
  