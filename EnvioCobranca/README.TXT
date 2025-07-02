-- view para envio de cobrança 

CREATE OR REPLACE VIEW enviarcobranca AS(
WITH titulos_abertos AS (
    SELECT 
        t.titu_empr,
        t.titu_fili,
        t.titu_clie,
        t.titu_titu,
        t.titu_seri,
        t.titu_parc,
        t.titu_venc,
        t.titu_valo,
        t.titu_linh_digi,
        t.titu_url_bole,
        t.titu_form_reci
    FROM titulosreceber t
    LEFT JOIN baretitulos b
        ON b.bare_titu = t.titu_titu
        AND b.bare_parc = t.titu_parc
        AND b.bare_seri = t.titu_seri
        AND b.bare_clie = t.titu_clie
        AND b.bare_empr = t.titu_empr
    WHERE 
        t.titu_aber = 'A'
        AND b.bare_titu IS NULL
        AND t.titu_venc BETWEEN '2025-07-01' AND '2025-07-31'
)

SELECT 
    t.titu_empr          AS empresa,
    t.titu_fili          AS filial,
    t.titu_clie          AS cliente_id,
    e.enti_nome          AS cliente_nome,
    e.enti_celu          AS cliente_celular,
    e.enti_fone          AS cliente_telefone,
    
    t.titu_titu          AS numero_titulo,
    t.titu_seri          AS serie,
    t.titu_parc          AS parcela,
    t.titu_venc          AS vencimento,
    t.titu_valo          AS valor,
    
    t.titu_form_reci     AS forma_recebimento_codigo,
    CASE t.titu_form_reci
        WHEN '00' THEN 'DUPLICATA'
        WHEN '01' THEN 'CHEQUE'
        WHEN '02' THEN 'PROMISSÓRIA'
        WHEN '03' THEN 'RECIBO'
        WHEN '50' THEN 'CHEQUE PRÉ'
        WHEN '51' THEN 'CARTÃO DE CRÉDITO'
        WHEN '52' THEN 'CARTÃO DE DÉBITO'
        WHEN '53' THEN 'BOLETO BANCÁRIO'
        WHEN '54' THEN 'DINHEIRO'
        WHEN '55' THEN 'DEPÓSITO EM CONTA'
        WHEN '56' THEN 'VENDA À VISTA'
        WHEN '60' THEN 'PIX'
        ELSE 'OUTRO'
    END                  AS forma_recebimento_nome,

    t.titu_linh_digi     AS linha_digitavel,
    t.titu_url_bole      AS url_boleto

FROM titulos_abertos t
LEFT JOIN entidades e
    ON e.enti_clie = t.titu_clie
    AND e.enti_empr = t.titu_empr
ORDER BY t.titu_venc
)