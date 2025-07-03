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