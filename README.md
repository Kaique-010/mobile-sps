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


ALTER TABLE sua_tabela
ADD COLUMN os_tota NUMERIC(15, 2);
