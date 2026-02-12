from django.db import models
from django.db.models import Sum
from decimal import Decimal


class SequencialControle(models.Model):
    seq_empr = models.CharField(max_length=100)
    seq_fili = models.CharField(max_length=100)
    seq_tipo = models.CharField(max_length=30)  # PRODUTO ou LOTE
    seq_chave_extra = models.CharField(max_length=100, null=True, blank=True)
    seq_atual = models.BigIntegerField(default=0)

    class Meta:
        db_table = "controle_de_sequenciais"
        unique_together = ("seq_empr", "seq_fili", "seq_tipo", "seq_chave_extra")
        
    def __str__(self):
        return f"{self.seq_empr} - {self.seq_fili} - {self.seq_tipo} - {self.seq_chave_extra}"


"""Modelo para representar uma fazenda."""
class Fazenda(models.Model):
    faze_nome = models.CharField(max_length=255)
    faze_loca = models.CharField(max_length=255, blank=True, null=True)
    faze_empr = models.CharField(max_length=100, db_column='faze_empr') 
    faze_fili = models.CharField(max_length=100, db_column='faze_fili')
    faze_area_tota = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Área total da fazenda (pode ser em hectares ou m²)",
        default=0
    )
      

    class Meta:
        db_table = 'agricola_fazendas'
        unique_together = ('faze_nome', 'faze_empr', 'faze_fili')

    def __str__(self):
        return f'Fazenda {self.id}: {self.faze_nome}'
    
    
    def atualizar_area_total(self):
        """Atualiza a área total somando as áreas dos talhões."""
        db_alias = self._state.db or 'default'
        # Talhao está definido abaixo, acessível em tempo de execução
        total = Talhao.objects.using(db_alias).filter(talh_faze=self.id).aggregate(total=Sum('talh_area'))['total'] or 0
        self.faze_area_tota = total
        self.save(using=db_alias)


"""Modelo para representar um talhão. herdando a fazenda empresa e filial."""
class Talhao(models.Model):
    talh_empr = models.CharField(max_length=100, db_column="talh_empr")
    talh_fili = models.CharField(max_length=100, db_column="talh_fili")
    talh_faze = models.IntegerField(db_column="talh_faze")
    talh_nome = models.CharField(max_length=255)
    talh_area = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Área do talhão (pode ser em hectares ou m²)"
    )
    talh_unmd = models.CharField(
        max_length=20, 
        default="hectares", 
        help_text="Unidade de medida da área (ex: hectares, m²)"
    )

    
    class Meta:
        db_table = 'agricola_talhoes'
        unique_together = ('talh_faze', 'talh_nome', 'talh_empr', 'talh_fili')
    
    def __str__(self):
        return f"{self.talh_nome} (Fazenda {self.talh_faze})"
        
    def save(self, *args, **kwargs):
        db_alias = kwargs.get('using') or self._state.db or 'default'
        super().save(*args, **kwargs)
        try:
            fazenda = Fazenda.objects.using(db_alias).get(id=self.talh_faze)
            fazenda.atualizar_area_total()
        except Fazenda.DoesNotExist:
            pass
        
    def delete(self, *args, **kwargs):
        db_alias = kwargs.get('using') or self._state.db or 'default'
        faze_id = self.talh_faze
        super().delete(*args, **kwargs)
        try:
            fazenda = Fazenda.objects.using(db_alias).get(id=faze_id)
            fazenda.atualizar_area_total()
        except Fazenda.DoesNotExist:
            pass
    
    
"""Modelo para representar uma categoria de produto agrícola."""
class CategoriaProduto(models.Model):
    cate_nome = models.CharField(max_length=255, unique=True)

    
    class Meta:
        db_table = 'categorias_produtos_agricolas'
    
    def __str__(self):
        return self.cate_nome


"""Modelo para representar um produto agrícola."""
class ProdutoAgro(models.Model):
    prod_codi_agro = models.CharField(max_length=100, unique=True)
    prod_nome_agro = models.CharField(max_length=255)
    prod_cate_agro = models.CharField(max_length=100, db_column="prod_cate_agro")
    prod_unmd_agro = models.CharField(max_length=50, choices=[('kg', 'Kilograma'), ('litro', 'Litro'), ('saco', 'Saco'), ('unidade', 'Unidade'), ('m²', 'Metro Quadrado'), ('ha', 'Hectare')])  # Ex: kg, litro, saco
    prod_desc_agro = models.TextField(blank=True, null=True, help_text="Descrição do produto agrícola")
    prod_cust_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Custo unitário do produto"
    )
    prod_empr_agro = models.CharField(max_length=100, db_column='empr_prod_agro')
    prod_fili_agro = models.CharField(max_length=100, db_column='fili_prod_agro')
    
    class Meta:
        db_table = 'agricola_produtos_agro'
        
    def __str__(self):
        return f"{self.prod_codi_agro} - {self.prod_nome_agro} ({self.prod_cate_agro})"
    

class LoteProdutos(models.Model):
    lote_empr = models.CharField(max_length=100, db_column='lote_empr')
    lote_fili = models.CharField(max_length=100, db_column='lote_fili')
    lote_ident = models.CharField(max_length=255, db_column="lote_ident", help_text="Identificador único do lote")
    lote_prod = models.CharField(max_length=100, db_column="lote_prod", help_text="Produto do lote")
    lote_quant = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Quantidade do produto no lote")
    lote_cust_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Custo unitário do lote"
    )
    lote_valo_vend = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Valor de venda unitário do lote"
    )
    lote_data_emi = models.DateField(null=True, blank=True, help_text="Data de emissão do lote")
    lote_data_venc = models.DateField(null=True, blank=True, help_text="Data de vencimento do lote")
    
    
    class Meta:
        db_table = 'produtos_lotes'
        unique_together = ('lote_empr', 'lote_fili', 'lote_ident', 'lote_prod')
        
    def __str__(self):
        return f"{self.lote_ident} - {self.lote_prod}"
    
"""Modelo para representar o estoque de um produto agrícola em uma fazenda."""
class EstoqueFazenda(models.Model):
    estq_faze = models.CharField(max_length=100, db_column="estq_faze")
    estq_prod = models.CharField(max_length=100, db_column="estq_prod")
    estq_quant = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Quantidade do produto no estoque")
    estq_cust_medi = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Custo médio atualizado com base nas movimentações"
    )
    estq_empr = models.CharField(max_length=100, db_column='estq_empr')
    estq_fili = models.CharField(max_length=100, db_column='estq_fili')
    
    class Meta:
        db_table = 'agricola_estoque_fazenda'
        unique_together = ('estq_empr', 'estq_fili', 'estq_faze', 'estq_prod')
        db_table = 'agricola_estoque_fazenda'
    
    def __str__(self):
        return f"{self.estq_faze} - {self.estq_prod}: {self.estq_quant}"


"""Modelo para representar as movimentações de estoque."""
class MovimentacaoEstoque(models.Model):
    TIPO_MOVIMENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]
    movi_estq_empr = models.CharField(max_length=100, db_column="movi_estq_empr")
    movi_estq_fili = models.CharField(max_length=100, db_column="movi_estq_fili")
    movi_estq_faze = models.CharField(max_length=100, db_column="movi_estq_faze")
    movi_estq_prod = models.CharField(max_length=100, db_column="movi_estq_prod")
    movi_estq_quant = models.DecimalField(max_digits=10, decimal_places=2)
    movi_estq_tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO_CHOICES)
    movi_estq_data = models.DateTimeField(auto_now_add=True)
    movi_estq_usua = models.CharField(max_length=100, db_column='usua_movi_estq')
    movi_estq_docu_refe = models.CharField(max_length=255, blank=True, null=True)
    movi_estq_moti = models.CharField(max_length=255, blank=True, null=True)
    movi_estq_cust_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Custo unitário na movimentação (para atualização do custo médio)"
    )
    movi_estq_cust_tota = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Custo total na movimentação (para atualização do custo médio)"
    )
    
    class Meta:
        db_table = 'agricola_movimentacao_estoque'
    
    def __str__(self):
        return f"{self.movi_estq_faze} - {self.movi_estq_prod} ({self.movi_estq_tipo} de {self.movi_estq_quant}) em {self.movi_estq_data}"

    def save(self, *args, **kwargs):
        # 1. Calcular custo total se não informado
        if self.movi_estq_cust_unit and not self.movi_estq_cust_tota:
            self.movi_estq_cust_tota = self.movi_estq_quant * self.movi_estq_cust_unit
        
        # 2. Atualizar EstoqueFazenda
        estoque, created = EstoqueFazenda.objects.get_or_create(
            estq_faze=self.movi_estq_faze,
            estq_prod=self.movi_estq_prod,
            estq_empr=self.movi_estq_empr,
            estq_fili=self.movi_estq_fili,
            defaults={'estq_quant': 0, 'estq_cust_medi': 0}
        )

        if self.movi_estq_tipo == 'entrada':
            # Média Ponderada Móvel
            custo_total_atual = estoque.estq_quant * estoque.estq_cust_medi
            custo_entrada = self.movi_estq_cust_tota or 0
            
            nova_quantidade = estoque.estq_quant + self.movi_estq_quant
            
            if nova_quantidade > 0:
                novo_custo_medio = (custo_total_atual + custo_entrada) / nova_quantidade
            else:
                novo_custo_medio = 0 # Evitar divisão por zero se algo estranho acontecer
                
            estoque.estq_quant = nova_quantidade
            estoque.estq_cust_medi = novo_custo_medio
            
        elif self.movi_estq_tipo == 'saida':
            # Na saída, a quantidade diminui, o custo médio permanece o mesmo
            estoque.estq_quant -= self.movi_estq_quant
            
            # Se não foi informado custo unitário na saída, usa o médio atual para registro
            if not self.movi_estq_cust_unit:
                self.movi_estq_cust_unit = estoque.estq_cust_medi
                self.movi_estq_cust_tota = self.movi_estq_quant * self.movi_estq_cust_unit
        
        estoque.save()
        super().save(*args, **kwargs)


"""Modelo para representar o histórico de movimentações de estoque."""
class HistoricoMovimentacao(models.Model):
    hist_movi = models.ForeignKey(MovimentacaoEstoque, on_delete=models.CASCADE, related_name="historico")
    hist_faze = models.CharField(max_length=100, db_column="hist_faze")
    hist_produto = models.CharField(max_length=100, db_column="hist_produto")
    hist_quant = models.DecimalField(max_digits=10, decimal_places=2)
    hist_tipo = models.CharField(max_length=10, choices=MovimentacaoEstoque.TIPO_MOVIMENTO_CHOICES)
    hist_data = models.DateTimeField(auto_now_add=True)
    hist_usuario = models.CharField(max_length=100, db_column="hist_usuario")   
    hist_obse = models.TextField(blank=True, null=True)
    hist_empr = models.CharField(max_length=100, db_column="hist_empr")
    hist_fili = models.CharField(max_length=100, db_column="hist_fili")
    class Meta:
        db_table = "agricola_historico_movimentacoes"

    def __str__(self):
        return f"{self.hist_faze} - {self.hist_produto} ({self.hist_tipo} de {self.hist_quant}) em {self.hist_data}"


"""Modelo para representar a aplicação de insumos em um talhão."""
class AplicacaoInsumos(models.Model):
    apli_talh = models.CharField(max_length=100, db_column="apli_talh")
    apli_prod = models.CharField(max_length=100, db_column="apli_prod")
    apli_quant = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Quantidade de insumo aplicada"
    )
    apli_data = models.DateTimeField(auto_now_add=True)
    apli_resp = models.CharField(max_length=100, db_column="apli_resp")
    apli_obse = models.TextField(blank=True, null=True)
    apli_empr = models.CharField(max_length=100, db_column="apli_empr")
    apli_fili = models.CharField(max_length=100, db_column="apli_fili")
    
    class Meta:
        db_table = 'agricola_aplicacao_insumos'
    
    def __str__(self):
        return f"Aplicação de {self.apli_prod} no {self.apli_talh} em {self.apli_data}"


"""Modelo para representar um animal."""
class Animal(models.Model):
    anim_faze = models.IntegerField(db_column="anim_faze")
    anim_ident = models.CharField(  
        max_length=100, 
        unique=True, 
        help_text="Número de identificação ou tag do animal"
    )
    anim_raca = models.CharField(max_length=100, blank=True, null=True)
    anim_data_nasc = models.DateField(blank=True, null=True)
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('F', 'Fêmea'),
    ]
    anim_sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    anim_peso_atual = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    anim_obse = models.TextField(blank=True, null=True)
    anim_empr = models.IntegerField(db_column="anim_empr")
    anim_fili = models.IntegerField(db_column="anim_fili")
    class Meta:
        db_table = 'agricola_animais'
    
    def __str__(self):
        return f"{self.anim_ident} (Fazenda {self.anim_faze})"


"""Modelo para representar eventos de um animal."""
class EventoAnimal(models.Model):
    EVENTO_CHOICES = [
        ('nascimento', 'Nascimento'),
        ('vacinacao', 'Vacinação'),
        ('engorda', 'Engorda'),
        ('abate', 'Abate'),
        ('venda', 'Venda'),
        # Outros eventos podem ser adicionados conforme a necessidade
    ]
    evnt_anim = models.CharField(max_length=100, db_column="evnt_anim_id")
    evnt_tipo_even = models.CharField(max_length=50, choices=EVENTO_CHOICES)
    evnt_data_even = models.DateField()
    evnt_cust = models.DecimalField(   
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        help_text="Custo associado a esse evento (se aplicável)"
    )
    evnt_desc = models.TextField(blank=True, null=True)
    evnt_usua = models.IntegerField(db_column="evnt_usua", null=True, blank=True)
    evnt_empr = models.IntegerField(db_column="evnt_empr")
    evnt_fili = models.IntegerField(db_column="evnt_fili")
    class Meta:
        db_table = 'agricola_eventos_animais'
    
    def __str__(self):
        return f"{self.evnt_anim} - {self.get_evnt_tipo_even_display()} em {self.evnt_data_even}"
