para trazer os preços ou os saldos ou informações correlatas fazemos isso como se fossem as fk mas como não são usamos anotates

da seguinte forma

nos produtos por exemplo :

relacionados as tabelas de saldos e tavela de preços para que as mesmas forneçam as informações que precisamos :

Informamos os campos no serializer

precos = serializers.SerializerMethodField()
prod_preco_vista = serializers.SerializerMethodField()
saldo_estoque = serializers.SerializerMethodField()

e na fazemos os gets como se fossem joins

para implementar o preço por exemplo a vista

fazemos:

def get_prod_preco_vista(self, obj):
banco = self.context.get("banco")
if not banco:
return None

        preco = Tabelaprecos.objects.using(banco).filter(
            tabe_prod=obj.prod_codi,
            tabe_empr=obj.prod_empr
        ).values_list('tabe_avis', flat=True).first()

        return preco

E depois na viewset passamos o na queryset ou no anotate se for uma função auxiliar

criamos uma variavel e passamos numa subquery na queryset

prod_preco_vista=Subquery(
Tabelaprecos.objects.filter(tabe_prod=OuterRef('prod_codi'))
.values('tabe_avis')[:1]
)

Pra trazer apenas os registros da empresa e filial logadas fazemos isso nas requisições do queryset também

mas aí pegamos a empresa e a filial da requisição do usuario e passamos isso on filtro

aí condicionamos junto do banco na lista seja do que for

def get_queryset(self):
banco = get_licenca_db_config(self.request)
empresa_id = self.request.headers.get("X-Empresa")
filial_id = self.request.headers.get("X-Filial")

    if banco and empresa_id and filial_id:
        data_minima = datetime(1900, 1, 1)
        return Contratosvendas.objects.using(banco).filter(
            Q(cont_data__gte=data_minima) | Q(cont_venc__gte=data_minima),
            cont_empr=empresa_id,
            cont_fili=filial_id
        )

    return Contratosvendas.objects.none()

    populando O.s

    DO

$$
DECLARE
    i INT := 1;
    setor_id INT;
BEGIN
    WHILE i <= 20 LOOP
        setor_id := ((i - 1) % 6) + 1;

        INSERT INTO ordemservico (
            orde_empr, orde_fili, orde_nume,  orde_data_aber, orde_hora_aber,
            orde_stat, orde_seto, orde_prio, orde_prob, orde_defe_desc,
            orde_obse, orde_plac, orde_enti, orde_usua_aber
        )
        VALUES (
            1, 1, i, CURRENT_DATE, CURRENT_TIME,
            '1', 1, 'normal', 'Problema simulado',
            'Defeito simulado', 'Observação qualquer', 'ABC1234', 100 + i, 999
        );

        -- Inserir peça
        INSERT INTO ordemservicopecas (
            peca_empr, peca_fili, peca_orde, peca_codi,
            peca_comp, peca_quan, peca_unit, peca_tota
        )
        VALUES (
            1, 1, i, CONCAT('P', LPAD(i::TEXT, 3, '0')),
            'Componente teste', 2, 10.50, 21.00
        );

        -- Inserir serviço
        INSERT INTO ordemservicoservicos (
            serv_empr, serv_fili, serv_orde, serv_codi,
            serv_comp, serv_quan, serv_unit, serv_tota
        )
        VALUES (
            1, 1, i, CONCAT('S', LPAD(i::TEXT, 3, '0')),
            'Serviço teste', 1, 50.00, 50.00
        );

        i := i + 1;
    END LOOP;
END;
$$;


inclui a coluna setor nos usuarios que vai refletir nas O.S

ALTER TABLE usuarios ADD COLUMN usua_seto INTEGER;
$$

ALTER TABLE os
ADD COLUMN os_tota NUMERIC(15, 2);

WITH orcado AS (
SELECT
o.plan_cont,
p.plan_nome,
CASE
WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END AS tipo,
        'JANEIRO' AS mes,
        o.plan_prev_jane AS valor
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'FEVEREIRO',
        o.plan_prev_feve
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'MARÇO',
        o.plan_prev_marc
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'ABRIL',
        o.plan_prev_abri
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'MAIO',
        o.plan_prev_maio
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'JUNHO',
        o.plan_prev_junh
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'JULHO',
        o.plan_prev_julh
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'AGOSTO',
        o.plan_prev_agos
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'SETEMBRO',
        o.plan_prev_sete
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'OUTUBRO',
        o.plan_prev_outu
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'NOVEMBRO',
        o.plan_prev_nove
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

    UNION ALL
    SELECT
        o.plan_cont,
        p.plan_nome,
        CASE
            WHEN LEFT(o.plan_cont::TEXT, 1) = '3' THEN 'RECEITA'
            WHEN LEFT(o.plan_cont::TEXT, 1) = '4' THEN 'DESPESA'

        END,
        'DEZEMBRO',
        o.plan_prev_deze
    FROM orcamentoplanocontas o
    JOIN planodecontas p ON o.plan_cont = p.plan_redu
    WHERE o.plan_exer = 2025

),

recebido AS (
SELECT
bare_cont::TEXT AS plan_redu,
p.plan_nome AS plano_nome,
TO_CHAR(bare_dpag, 'MM') AS mes_num,
CASE EXTRACT(MONTH FROM bare_dpag)
WHEN 1 THEN 'JANEIRO'
WHEN 2 THEN 'FEVEREIRO'
WHEN 3 THEN 'MARÇO'
WHEN 4 THEN 'ABRIL'
WHEN 5 THEN 'MAIO'
WHEN 6 THEN 'JUNHO'
WHEN 7 THEN 'JULHO'
WHEN 8 THEN 'AGOSTO'
WHEN 9 THEN 'SETEMBRO'
WHEN 10 THEN 'OUTUBRO'
WHEN 11 THEN 'NOVEMBRO'
WHEN 12 THEN 'DEZEMBRO'
ELSE 'MÊS_DESCONHECIDO'
END AS mes,
SUM(bare_pago) AS valor_recebido
FROM baretitulos
LEFT JOIN planodecontas p ON p.plan_redu::TEXT = baretitulos.bare_cont::TEXT
WHERE bare_pago IS NOT NULL
AND EXTRACT(YEAR FROM bare_dpag) = 2025
AND bare_empr = 1  
 AND bare_fili = 1  
GROUP BY
bare_cont,
p.plan_nome,
TO_CHAR(bare_dpag, 'MM'),
EXTRACT(MONTH FROM bare_dpag)
ORDER BY mes_num
),

pago AS (
SELECT
bapa_cont::TEXT AS plan_redu,
p.plan_nome AS plano_nome,
TO_CHAR(bapa_dpag, 'MM') AS mes_num,
CASE EXTRACT(MONTH FROM bapa_dpag)
WHEN 1 THEN 'JANEIRO'
WHEN 2 THEN 'FEVEREIRO'
WHEN 3 THEN 'MARÇO'
WHEN 4 THEN 'ABRIL'
WHEN 5 THEN 'MAIO'
WHEN 6 THEN 'JUNHO'
WHEN 7 THEN 'JULHO'
WHEN 8 THEN 'AGOSTO'
WHEN 9 THEN 'SETEMBRO'
WHEN 10 THEN 'OUTUBRO'
WHEN 11 THEN 'NOVEMBRO'
WHEN 12 THEN 'DEZEMBRO'
ELSE 'MÊS_DESCONHECIDO'
END AS mes,
SUM(bapa_pago) AS valor_pago
FROM bapatitulos
LEFT JOIN planodecontas p ON p.plan_redu::TEXT = bapatitulos.bapa_cont::TEXT
WHERE bapa_pago IS NOT NULL
AND EXTRACT(YEAR FROM bapa_dpag) = 2025
AND bapa_empr = 1  
 AND bapa_fili = 1  
GROUP BY
bapa_cont,
p.plan_nome,
TO_CHAR(bapa_dpag, 'MM'),
EXTRACT(MONTH FROM bapa_dpag)
ORDER BY mes_num

),

unificado AS (
SELECT
COALESCE(o.plan_cont::TEXT, r.plan_redu, p.plan_redu) AS plan_redu,
o.plan_nome,
o.tipo,
COALESCE(o.mes, r.mes, p.mes) AS mes,
COALESCE(o.valor, 0) AS valor_orcado,
COALESCE(r.valor_recebido, 0) AS valor_recebido,
COALESCE(p.valor_pago, 0) AS valor_pago
FROM orcado o
FULL OUTER JOIN (
pago p FULL OUTER JOIN recebido r
ON p.plan_redu = r.plan_redu AND p.mes = r.mes
) ON o.plan_cont::TEXT = COALESCE(p.plan_redu, r.plan_redu) AND o.mes = COALESCE(p.mes, r.mes)

)

SELECT \*
FROM unificado
WHERE
COALESCE(valor_orcado, 0) <> 0
OR COALESCE(valor_recebido, 0) <> 0
OR COALESCE(valor_pago, 0) <> 0
ORDER BY tipo, plan_redu, mes;
