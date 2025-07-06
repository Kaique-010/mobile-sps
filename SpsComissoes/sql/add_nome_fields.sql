-- Script SQL para adicionar os campos de nome do cliente e funcionário
-- na tabela comissoes_sps

-- Adicionar campo para nome do funcionário
ALTER TABLE comissoes_sps ADD COLUMN comi_func_nome VARCHAR(100);

-- Adicionar campo para nome do cliente
ALTER TABLE comissoes_sps ADD COLUMN comi_clie_nome VARCHAR(100);

-- Comentários dos campos
COMMENT ON COLUMN comissoes_sps.comi_func_nome IS 'Nome do funcionário responsável pela comissão';
COMMENT ON COLUMN comissoes_sps.comi_clie_nome IS 'Nome do cliente da comissão';

-- Script para popular os nomes existentes (opcional)
-- UPDATE comissoes_sps 
-- SET comi_func_nome = (SELECT enti_nome FROM entidades WHERE enti_clie = CAST(comissoes_sps.comi_func AS INTEGER) AND enti_tipo_enti IN ('FU', 'VE') LIMIT 1)
-- WHERE comi_func_nome IS NULL AND comi_func IS NOT NULL;

-- UPDATE comissoes_sps 
-- SET comi_clie_nome = (SELECT enti_nome FROM entidades WHERE enti_clie = CAST(comissoes_sps.comi_clie AS INTEGER) AND enti_tipo_enti IN ('CL', 'AM') LIMIT 1)
-- WHERE comi_clie_nome IS NULL AND comi_clie IS NOT NULL;