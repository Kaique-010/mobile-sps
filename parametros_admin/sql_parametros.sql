-- Script SQL para popular parâmetros do sistema
-- Execute este script após criar o sistema de parâmetros

-- =====================================================
-- PARÂMETROS DE ESTOQUE
-- =====================================================

-- Entrada automática de estoque
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,  -- Ajustar conforme empresa
    1 as para_fili,  -- Ajustar conforme filial
    m.modu_codi as para_modu,
    'entrada_automatica_estoque' as para_nome,
    'true' as para_valo,
    'Permite entrada automática de estoque ao receber mercadorias' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- Saída automática de estoque
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'saida_automatica_estoque' as para_nome,
    'true' as para_valo,
    'Permite saída automática de estoque em vendas/pedidos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- Permitir estoque negativo
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'permitir_estoque_negativo' as para_nome,
    'false' as para_valo,
    'Permite que o estoque fique negativo' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- Alerta de estoque mínimo
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'alerta_estoque_minimo' as para_nome,
    'true' as para_valo,
    'Exibe alertas quando estoque atingir o mínimo' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- Cálculo automático de custo
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'calculo_automatico_custo' as para_nome,
    'true' as para_valo,
    'Calcula automaticamente o custo médio dos produtos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- Pedido volta estoque
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'pedido_volta_estoque' as para_nome,
    'true' as para_valo,
    'Retorna produtos ao estoque quando pedido é cancelado' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'
LIMIT 1;

-- =====================================================
-- PARÂMETROS DE PEDIDOS
-- =====================================================

-- Usar preço a prazo
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'usar_preco_prazo' as para_nome,
    'false' as para_valo,
    'Utiliza preço a prazo por padrão em pedidos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'
LIMIT 1;

-- Usar último preço
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'usar_ultimo_preco' as para_nome,
    'true' as para_valo,
    'Utiliza o último preço aplicado para o cliente' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'
LIMIT 1;

-- Desconto em pedido
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'desconto_pedido' as para_nome,
    'true' as para_valo,
    'Permite aplicar desconto em pedidos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'
LIMIT 1;

-- Validar estoque em pedido
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'validar_estoque_pedido' as para_nome,
    'true' as para_valo,
    'Valida disponibilidade de estoque antes de confirmar pedido' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    1 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'
LIMIT 1;

-- Calcular frete automático
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'calcular_frete_automatico' as para_nome,
    'false' as para_valo,
    'Calcula frete automaticamente baseado no CEP' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'
LIMIT 1;

-- =====================================================
-- PARÂMETROS DE ORÇAMENTOS
-- =====================================================

-- Baixa de estoque em orçamento
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'baixa_estoque_orcamento' as para_nome,
    'false' as para_valo,
    'Permite baixa de estoque ao confirmar orçamento' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- Usar preço a prazo em orçamento
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'usar_preco_prazo' as para_nome,
    'false' as para_valo,
    'Utiliza preço a prazo por padrão em orçamentos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- Usar último preço em orçamento
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'usar_ultimo_preco' as para_nome,
    'true' as para_valo,
    'Utiliza o último preço aplicado em orçamentos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- Desconto em orçamento
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'desconto_orcamento' as para_nome,
    'true' as para_valo,
    'Permite aplicar desconto em orçamentos' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- Validade do orçamento em dias
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'validade_orcamento_dias' as para_nome,
    '30' as para_valo,
    'Quantidade de dias de validade do orçamento' as para_desc,
    1 as para_ativ,
    'INTEGER' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- Conversão automática para pedido
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    1 as para_empr,
    1 as para_fili,
    m.modu_codi as para_modu,
    'conversao_automatica_pedido' as para_nome,
    'true' as para_valo,
    'Permite conversão automática de orçamento para pedido' as para_desc,
    1 as para_ativ,
    'BOOLEAN' as para_tipo,
    0 as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM modulo m 
WHERE m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'
LIMIT 1;

-- =====================================================
-- SCRIPT PARA MÚLTIPLAS EMPRESAS/FILIAIS
-- =====================================================

-- Para aplicar os parâmetros em todas as empresas/filiais existentes,
-- descomente e execute o bloco abaixo:

/*
-- Inserir parâmetros para todas as combinações empresa/filial
INSERT INTO parametro_sistema (para_empr, para_fili, para_modu, para_nome, para_valo, para_desc, para_ativ, para_tipo, para_obri, para_cria, para_alte)
SELECT 
    e.empr_codi as para_empr,
    f.fili_codi as para_fili,
    m.modu_codi as para_modu,
    param.nome as para_nome,
    param.valor as para_valo,
    param.descricao as para_desc,
    1 as para_ativ,
    param.tipo as para_tipo,
    param.obrigatorio as para_obri,
    NOW() as para_cria,
    NOW() as para_alte
FROM empresa e
CROSS JOIN filial f
CROSS JOIN modulo m
CROSS JOIN (
    SELECT 'entrada_automatica_estoque' as nome, 'true' as valor, 'Permite entrada automática de estoque' as descricao, 'BOOLEAN' as tipo, 1 as obrigatorio, 'estoque' as modulo_tipo
    UNION ALL
    SELECT 'saida_automatica_estoque', 'true', 'Permite saída automática de estoque', 'BOOLEAN', 1, 'estoque'
    UNION ALL
    SELECT 'permitir_estoque_negativo', 'false', 'Permite estoque negativo', 'BOOLEAN', 1, 'estoque'
    UNION ALL
    SELECT 'usar_preco_prazo', 'false', 'Usar preço a prazo', 'BOOLEAN', 0, 'pedido'
    UNION ALL
    SELECT 'desconto_pedido', 'true', 'Permitir desconto em pedidos', 'BOOLEAN', 0, 'pedido'
    UNION ALL
    SELECT 'baixa_estoque_orcamento', 'false', 'Baixa estoque em orçamento', 'BOOLEAN', 0, 'orcamento'
    UNION ALL
    SELECT 'validade_orcamento_dias', '30', 'Dias de validade do orçamento', 'INTEGER', 0, 'orcamento'
) param
WHERE f.fili_empr = e.empr_codi
AND (
    (param.modulo_tipo = 'estoque' AND (m.modu_nome LIKE '%estoque%' OR m.modu_nome LIKE '%Estoque%'))
    OR (param.modulo_tipo = 'pedido' AND (m.modu_nome LIKE '%pedido%' OR m.modu_nome LIKE '%Pedido%'))
    OR (param.modulo_tipo = 'orcamento' AND (m.modu_nome LIKE '%orcamento%' OR m.modu_nome LIKE '%Orcamento%'))
)
AND NOT EXISTS (
    SELECT 1 FROM parametro_sistema ps 
    WHERE ps.para_empr = e.empr_codi 
    AND ps.para_fili = f.fili_codi 
    AND ps.para_modu = m.modu_codi 
    AND ps.para_nome = param.nome
);
*/

-- =====================================================
-- VERIFICAÇÃO DOS PARÂMETROS INSERIDOS
-- =====================================================

-- Consulta para verificar os parâmetros inseridos
SELECT 
    ps.para_empr as empresa,
    ps.para_fili as filial,
    m.modu_nome as modulo,
    ps.para_nome as parametro,
    ps.para_valo as valor,
    ps.para_desc as descricao,
    ps.para_ativ as ativo,
    ps.para_tipo as tipo
FROM parametro_sistema ps
JOIN modulo m ON ps.para_modu = m.modu_codi
WHERE ps.para_nome IN (
    'entrada_automatica_estoque',
    'saida_automatica_estoque', 
    'permitir_estoque_negativo',
    'alerta_estoque_minimo',
    'calculo_automatico_custo',
    'pedido_volta_estoque',
    'usar_preco_prazo',
    'usar_ultimo_preco',
    'desconto_pedido',
    'validar_estoque_pedido',
    'calcular_frete_automatico',
    'baixa_estoque_orcamento',
    'desconto_orcamento',
    'validade_orcamento_dias',
    'conversao_automatica_pedido'
)
ORDER BY ps.para_empr, ps.para_fili, m.modu_nome, ps.para_nome;

-- =====================================================
-- COMANDOS DE LIMPEZA (USE COM CUIDADO)
-- =====================================================

-- Para remover todos os parâmetros criados (descomente se necessário):
/*
DELETE FROM parametro_sistema 
WHERE para_nome IN (
    'entrada_automatica_estoque',
    'saida_automatica_estoque', 
    'permitir_estoque_negativo',
    'alerta_estoque_minimo',
    'calculo_automatico_custo',
    'pedido_volta_estoque',
    'usar_preco_prazo',
    'usar_ultimo_preco',
    'desconto_pedido',
    'validar_estoque_pedido',
    'calcular_frete_automatico',
    'baixa_estoque_orcamento',
    'desconto_orcamento',
    'validade_orcamento_dias',
    'conversao_automatica_pedido'
);
*/