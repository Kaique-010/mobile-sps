from django.db import models
from django.utils.html import mark_safe




class Lote(models.Model):
    lote_empr = models.IntegerField()
    lote_prod = models.CharField(max_length=60)
    lote_lote = models.IntegerField()
    lote_unit = models.DecimalField(max_digits=15, decimal_places=2, help_text="Preço unitário") 
    lote_sald = models.DecimalField(max_digits=15, decimal_places=2, help_text="Saldo") 
    lote_usua = models.IntegerField()
    lote_data_alt = models.DateTimeField(auto_now=True, help_text="Data de alteração")
    lote_data_venc = models.DateField(help_text="Data de vencimento")
    lote_ativ = models.BooleanField(default=True, help_text="Lote ativo")
    lote_data_fabr = models.DateField(blank=True, null=True, help_text="Data de fabricação")
    lote_obse= models.TextField(blank=True, null=True, help_text="Observações do lote")
    
    class Meta:
        db_table = 'lotesvenda'
        verbose_name = 'Lote de Venda'
        verbose_name_plural = 'Lotes de Venda'
        ordering = ['lote_empr','lote_prod', 'lote_lote']
        unique_together = ('lote_empr', 'lote_prod', 'lote_lote')
        managed = False

    def __str__(self):
        return f'{self.lote_lote} - {self.lote_prod}'
    
    @property
    def dias_para_vencimento(self):
        """Calcula quantos dias faltam para o vencimento"""
        if self.lote_data_venc:
            delta = self.lote_data_venc - date.today()
            return delta.days
        return None
    
    @property
    def vencido(self):
        """Verifica se o lote está vencido"""
        dias = self.dias_para_vencimento
        return dias is not None and dias < 0
    
    @property
    def proximo_vencimento(self):
        """Verifica se o lote está próximo do vencimento (30 dias)"""
        dias = self.dias_para_vencimento
        return dias is not None and 0 <= dias <= 30
    
    @property
    def status_vencimento(self):
        """Retorna status do vencimento"""
        if self.vencido:
            return 'VENCIDO'
        elif self.proximo_vencimento:
            return 'PRÓXIMO_VENCIMENTO'
        return 'VÁLIDO'
    
    @classmethod
    def proximo_numero_lote(cls, empresa, produto):
        """Gera próximo número de lote sequencial"""
        ultimo_lote = cls.objects.filter(
            lote_empr=empresa,
            lote_prod=produto
        ).aggregate(models.Max('lote_lote'))['lote_lote__max']
        
        return (ultimo_lote or 0) + 1
    
    def save(self, *args, **kwargs):
        """Override save para validações"""
        if not self.lote_data_fabr:
            self.lote_data_fabr = date.today()
        
        # Se não tem data de vencimento, calcula baseado na fabricação
        if not self.lote_data_venc and self.lote_data_fabr:
            self.lote_data_venc = self.lote_data_fabr + timedelta(days=365)
        
        super().save(*args, **kwargs)


class GrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='grup_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='grup_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'gruposprodutos'
        verbose_name = 'Grupo de Produto'
        verbose_name_plural = 'Grupos de Produtos'
        managed = 'false'


    def __str__(self):
        return f'{self.codigo} - {self.descricao}'

class SubgrupoProduto(models.Model):
    codigo = models.AutoField(
        db_column='sugr_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='sugr_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'subgruposprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class FamiliaProduto(models.Model):
    codigo = models.AutoField(
        db_column='fami_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255, 
        db_column='fami_desc', 
        verbose_name='Descrição'
    )

    class Meta:
        db_table = 'familiaprodutos'
        managed = 'false'



    def __str__(self):
        return self.descricao

class Marca(models.Model):
    codigo = models.AutoField(
        db_column='marc_codi', 
        primary_key=True,
        verbose_name='Código'
    )
    nome = models.CharField(
        max_length=255, 
        db_column='marc_desc', 
        verbose_name='Nome'
    )

    class Meta:
        db_table = 'marca'
        managed = 'false'



    def __str__(self):
        return self.nome

class Tabelaprecos(models.Model):
    tabe_empr = models.IntegerField(primary_key=True)  
    tabe_fili = models.IntegerField()
    tabe_prod = models.CharField("Produtos", max_length=60, db_column='tabe_prod')
    tabe_prco = models.DecimalField("Preço", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms = models.DecimalField("ICMS", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desc = models.DecimalField("Desconto", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vipi = models.DecimalField("Valor IPI", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi = models.DecimalField("% IPI", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret = models.DecimalField("Frete", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_desp = models.DecimalField("Despesas", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_cust = models.DecimalField("Custo", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg = models.DecimalField("Margem", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_impo = models.DecimalField("Impostos", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis = models.DecimalField("Preço à Vista", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz = models.DecimalField("Prazo", max_digits=15, decimal_places=4, blank=True, null=True)
    tabe_apra = models.DecimalField("Preço a Prazo", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_vare = models.DecimalField("Varejo", max_digits=15, decimal_places=2, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True) 
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True) 
    tabe_valo_st = models.DecimalField("Valor ST", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_perc_reaj = models.DecimalField("% Reajuste", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField("Histórico", blank=True, null=True)
    tabe_cuge = models.DecimalField("Custo Geral", max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_entr = models.DateField("Data Entrada", blank=True, null=True)
    tabe_perc_st = models.DecimalField("% ST", max_digits=7, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = 'tabelaprecos'
        unique_together = (('tabe_empr', 'tabe_fili', 'tabe_prod'),)
        managed = False
        verbose_name = 'Tabela de Preço'
        verbose_name_plural = 'Tabelas de Preços'

    def __str__(self):
        return f"{self.tabe_prod} - R$ {self.tabe_prco or 0:.2f}"

    @property
    def preco_formatado(self):
        return f"R$ {self.tabe_prco or 0:.2f}"

class UnidadeMedida(models.Model):
    unid_codi = models.CharField(max_length=10, db_column='unid_codi', primary_key=True) 
    unid_desc = models.CharField(max_length=50, db_column='unid_desc') 
    

    class Meta:
        db_table = 'unidadesmedidas'
        managed = 'false'


    def __str__(self):
        return self.unid_desc


class Produtos(models.Model):
    prod_empr = models.CharField(max_length=50, db_column='prod_empr')
    prod_codi = models.CharField(max_length=50, db_column='prod_codi', primary_key=True) 
    prod_nome = models.CharField(max_length=255, db_column='prod_nome') 
    prod_unme = models.ForeignKey(UnidadeMedida,on_delete=models.PROTECT, db_column='prod_unme') 
    prod_grup= models.ForeignKey(GrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_grup', related_name='produtos', blank= True, null= True) 
    prod_sugr = models.ForeignKey(SubgrupoProduto, on_delete=models.DO_NOTHING, db_column='prod_sugr', related_name='produtos', blank= True, null= True) 
    prod_fami= models.ForeignKey(FamiliaProduto, on_delete=models.DO_NOTHING, db_column='prod_fami', related_name='produtos', blank= True, null= True) 
    prod_loca = models.CharField(max_length=255, db_column='prod_loca', blank= True, null= True) 
    prod_ncm = models.CharField(max_length=10, db_column='prod_ncm') 
    prod_marc = models.ForeignKey(Marca, on_delete=models.DO_NOTHING, db_column='prod_marc', related_name='produtos', blank= True, null= True) 
    prod_coba = models.CharField(max_length=50, db_column='prod_coba', blank= True, null= True)
    prod_foto = models.BinaryField(db_column='prod_foto', blank=True, null=True) 
    prod_cera_m2cx = models.DecimalField(max_digits=15, decimal_places=2, db_column='prod_cera_m2cx', blank=True, null=True)
    prod_cera_pccx = models.DecimalField(max_digits=15, decimal_places=2, db_column='prod_cera_pccx', blank=True, null=True)
    #prod_lote = models.CharField(max_length=50, blank=True, null=True, help_text="Lote de produção")
    #prod_lote_venc = models.DateField(blank=True, null=True, help_text="Data de vencimento do lote")



    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        managed = 'false'

    def __str__(self):
        return self.prod_codi
    
    def imagem_tag(self):
        try:
            return mark_safe(f'<img src="{self.foto.url}" width="80" height="80" />')
        except AttributeError:
            return "Sem foto"

    imagem_tag.short_description = 'Imagem'


class SaldoProduto(models.Model):
    produto_codigo = models.ForeignKey(Produtos, on_delete=models.CASCADE, db_column='sapr_prod', primary_key=True)
    empresa = models.CharField(max_length=50, db_column='sapr_empr')
    filial = models.CharField(max_length=50, db_column='sapr_fili')
    saldo_estoque = models.DecimalField(max_digits=10, decimal_places=2, db_column='sapr_sald')

    class Meta:
        db_table = 'saldosprodutos'
        managed = False
        unique_together = (('produto_codigo', 'empresa', 'filial'),)
        constraints = [
            models.UniqueConstraint(
                fields=['produto_codigo', 'empresa', 'filial'],
                name='saldosprodutos_pk'
            )
        ]

    
        




class Tabelaprecoshist(models.Model):
    tabe_id = models.AutoField(primary_key=True)
    tabe_empr = models.IntegerField()
    tabe_fili = models.IntegerField()
    tabe_prod = models.CharField(max_length=20)
    tabe_data_hora = models.DateTimeField()
    tabe_perc_reaj = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_avis_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_apra_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_hist = models.TextField(blank=True, null=True)
    tabe_prco_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_prco_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_pipi_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_fret_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_desp_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cust_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_cuge_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_icms_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_impo_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_impo_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_marg_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_praz_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_valo_st_ante = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tabe_valo_st_novo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tabelaprecoshist'



#Produtos detalhados 
class ProdutosDetalhados(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    nome = models.CharField(max_length=255)
    unidade = models.CharField(max_length=10)
    grupo_id = models.CharField(max_length=20, null=True)
    grupo_nome = models.CharField(max_length=255, null=True)
    marca_id = models.CharField(max_length=20, null=True)
    marca_nome = models.CharField(max_length=255, null=True)
    custo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    preco_vista = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    preco_prazo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    foto = models.TextField(null=True)
    peso_bruto = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    peso_liquido = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    empresa = models.CharField(max_length=20, null=True)
    filial = models.CharField(max_length=20, null=True)
    valor_total_estoque = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    valor_total_venda_vista = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    valor_total_venda_prazo = models.DecimalField(max_digits=14, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 'produtos_detalhados'


