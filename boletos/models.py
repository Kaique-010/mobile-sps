from django.db import models


class Titulosreceber(models.Model):
    titu_empr = models.IntegerField()
    titu_fili = models.IntegerField()
    titu_clie = models.IntegerField()
    # Identificação
    titu_titu = models.CharField(max_length=13)
    titu_seri = models.CharField(max_length=5)
    titu_parc = models.CharField(max_length=3)
    # Datas básicas
    titu_emis = models.DateField(blank=True, null=True)
    titu_venc = models.DateField(blank=True, null=True)
    # Valor
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    # Nosso número / controle bancário
    titu_noss_nume = models.CharField(max_length=30, blank=True, null=True)
    titu_noss_nume_form = models.CharField(max_length=50, blank=True, null=True)
    # Linha digitável / URL boleto
    titu_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    titu_url_bole = models.CharField(max_length=255, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'titulosreceber'
        

class Remessaretorno(models.Model):
    bole_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bole_obse = models.TextField(blank=True, null=True)
    bole_banc = models.IntegerField(blank=True, null=True)
    bole_cart = models.IntegerField(blank=True, null=True)
    bole_noss = models.CharField(max_length=30, blank=True, null=True)
    bole_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    bole_nome_arqu = models.CharField(max_length=100, blank=True, null=True)
    bole_data_rece = models.DateField(blank=True, null=True)
    bole_valo_rece = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boleto'


class Boleto(models.Model):
    bole_empr = models.IntegerField()
    bole_fili = models.IntegerField()
    bole_soci = models.CharField(max_length=15)
    bole_titu = models.CharField(max_length=13)
    bole_seri = models.CharField(max_length=3)
    bole_parc = models.CharField(max_length=3)
    bole_emis = models.DateField(blank=True, null=True)
    bole_venc = models.DateField(blank=True, null=True)
    bole_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bole_obse = models.TextField(blank=True, null=True)
    bole_banc = models.IntegerField(blank=True, null=True)
    bole_cart = models.IntegerField(blank=True, null=True)
    bole_noss = models.CharField(max_length=30, blank=True, null=True)
    bole_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    bole_nome_arqu = models.CharField(max_length=100, blank=True, null=True)
    bole_data_rece = models.DateField(blank=True, null=True)
    bole_valo_rece = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boleto'


class Boletoscancelados(models.Model):
    id = models.IntegerField(primary_key=True)
    linh_digi = models.CharField(max_length=255)
    canc_data = models.DateField(blank=True, null=True)
    canc_moti = models.TextField(blank=True, null=True)
    canc_usua = models.IntegerField(blank=True, null=True)
    canc_nome_usua = models.CharField(max_length=60, blank=True, null=True)
    canc_codi_prot_naci = models.IntegerField(blank=True, null=True)


    class Meta:
        managed = False
        db_table = 'boletoscancelados'
        unique_together = (('id', 'linh_digi'),)


# ====== models/bordero.py ======
from django.utils import timezone


class Bordero(models.Model):
    empresa = models.IntegerField()
    filial = models.IntegerField()


    data = models.DateField(default=timezone.now)
    banco = models.CharField(max_length=4) # Ex: 001, 341, 104
    arquivo_remessa = models.FileField(upload_to="remessas/")
    arquivo_retorno = models.FileField(upload_to="retornos/", null=True, blank=True)


    status = models.IntegerField(choices=[
                                    (0, "Gerado"),
                                    (1, "Enviado"),
                                    (2, "Processado Retorno")
                                    ],
                                    default=0
                                    )


    class Meta:
        db_table = "fin_bordero"


        def __str__(self):
            return f"Bordero {self.id} - Banco {self.banco} - Status {self.get_status_display()}"



class Carteira(models.Model):
    cart_empr = models.IntegerField()
    cart_banc = models.IntegerField()
    cart_codi = models.IntegerField()
    cart_nome = models.CharField(max_length=60, primary_key=True)
    cart_conv = models.CharField(max_length=20, blank=True, null=True)
    cart_mens_loca = models.CharField(max_length=120, blank=True, null=True)
    cart_espe = models.CharField(max_length=10, blank=True, null=True)
    cart_acei = models.IntegerField(blank=True, null=True)
    cart_cart = models.CharField(max_length=10, blank=True, null=True)
    cart_noss_nume = models.CharField(max_length=30, blank=True, null=True)
    cart_prot = models.IntegerField(blank=True, null=True)
    cart_mult = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cart_juro = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
    cart_desc = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    cart_inst1 = models.CharField(max_length=20, blank=True, null=True)
    cart_inst2 = models.CharField(max_length=20, blank=True, null=True)
    cart_mens = models.TextField(blank=True, null=True)
    cart_past_reme = models.TextField(blank=True, null=True)
    cart_pref_reme = models.CharField(max_length=20, blank=True, null=True)
    cart_nume_arqu = models.IntegerField(blank=True, null=True)
    cart_past_reto = models.TextField(blank=True, null=True)
    cart_obse = models.TextField(blank=True, null=True)
    cart_codi_cede = models.CharField(max_length=30, blank=True, null=True)
    cart_cnab = models.IntegerField(blank=True, null=True)
    cart_bole = models.IntegerField(blank=True, null=True)
    cart_codi_tran = models.CharField(max_length=20, blank=True, null=True)
    cart_espe_moed = models.CharField(max_length=20, blank=True, null=True)
    cart_moda = models.CharField(max_length=15, blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    cart_tipo_docu = models.IntegerField(blank=True, null=True)
    cart_baix = models.IntegerField(blank=True, null=True)
    cart_praz_desc = models.IntegerField(blank=True, null=True)
    cart_cara_titu = models.IntegerField(blank=True, null=True)
    cart_nega = models.CharField(max_length=1, blank=True, null=True)
    cart_fili = models.IntegerField()
    cart_webs_clie_id = models.TextField(blank=True, null=True)
    cart_webs_clie_secr = models.TextField(blank=True, null=True)
    cart_webs_user_key = models.TextField(blank=True, null=True)
    cart_webs_indi_pix = models.BooleanField(blank=True, null=True)
    cart_webs_ssl_lib = models.CharField(max_length=30, blank=True, null=True)
    cart_webs_scop = models.CharField(max_length=255, blank=True, null=True)
    cart_webs_tipo_chav_pix = models.IntegerField(blank=True, null=True)
    cart_webs_crt = models.CharField(max_length=200, blank=True, null=True)
    cart_webs_key = models.CharField(max_length=200, blank=True, null=True)
    cart_webs_chav_pix = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'carteira'
        unique_together = (('cart_empr', 'cart_banc', 'cart_codi'),)

    @classmethod
    def next_code(cls, banco, empresa, filial=None, using='default'):
        from django.db.models import Max
        try:
            qs = cls.objects.using(using).filter(cart_empr=empresa, cart_banc=banco)
            if filial is not None:
                qs = qs.filter(cart_fili=filial)
            max_code = qs.aggregate(Max('cart_codi'))['cart_codi__max'] or 0
            return int(max_code) + 1
        except Exception:
            return 1

    @classmethod
    def lookup(cls, banco, empresa, codigo, filial=None, using='default'):
        try:
            qs = cls.objects.using(using).filter(cart_empr=empresa, cart_banc=banco, cart_codi=codigo)
            if filial is not None:
                qs = qs.filter(cart_fili=filial)
            return qs.first()
        except Exception:
            return None

    def as_dict(self):
        return {
            'cart_empr': self.cart_empr,
            'cart_banc': self.cart_banc,
            'cart_codi': self.cart_codi,
            'cart_nome': self.cart_nome,
            'cart_conv': self.cart_conv,
            'cart_cart': self.cart_cart,
            'cart_noss_nume': self.cart_noss_nume,
            'cart_cnab': self.cart_cnab,
            'cart_mult': float(self.cart_mult or 0),
            'cart_juro': float(self.cart_juro or 0),
            'cart_desc': float(self.cart_desc or 0),
            'cart_mens_loca': self.cart_mens_loca,
            'cart_codi_tran': self.cart_codi_tran,
            'cart_codi_cede': self.cart_codi_cede,
            'cart_espe': self.cart_espe,
            'cart_espe_moed': self.cart_espe_moed,
            'cart_acei': self.cart_acei,
            'cart_nume_arqu': self.cart_nume_arqu,
            'cart_bole': self.cart_bole,
            'cart_tipo_docu': self.cart_tipo_docu,
            'cart_baix': self.cart_baix,
            'cart_prot': self.cart_prot,
            'cart_nega': self.cart_nega,
            'cart_webs_clie_id': self.cart_webs_clie_id,
            'cart_webs_clie_secr': self.cart_webs_clie_secr,
            'cart_webs_user_key': self.cart_webs_user_key,
            'cart_webs_scop': self.cart_webs_scop,
            'cart_webs_indi_pix': bool(self.cart_webs_indi_pix) if self.cart_webs_indi_pix is not None else False,
            'cart_webs_chav_pix': self.cart_webs_chav_pix,
            'cart_webs_crt': self.cart_webs_crt,
            'cart_webs_key': self.cart_webs_key,
        }
