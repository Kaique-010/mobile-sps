from django.db import models
import json
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password as django_check_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager



class UsuariosManager(BaseUserManager):
    def get_by_natural_key(self, username):
        return self.get(usua_nome=username)

    def create_user(self, usua_nome, password=None, **extra_fields):
        if not usua_nome:
            raise ValueError("O campo 'usua_nome' é obrigatório")

        # Remove campos que o model não suporta (do legado)
        extra_fields.pop('is_superuser', None)
        extra_fields.pop('is_staff', None)
        extra_fields.pop('is_active', None)

        user = self.model(usua_nome=usua_nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usua_nome, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(usua_nome, password, **extra_fields)


class Usuarios(AbstractBaseUser, PermissionsMixin):
    usua_codi = models.AutoField(primary_key=True)
    usua_nome = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128, db_column='usua_senh_mobi')
    usua_seto = models.IntegerField(db_column='usua_seto', blank=True, null=True) 
    USERNAME_FIELD = 'usua_nome'
    PASSWORD_FIELD = 'password'
    REQUIRED_FIELDS = []

    objects = UsuariosManager()

    class Meta:
        db_table = 'usuarios'
        managed = False

    def __str__(self):
        return self.usua_nome

    def check_password(self, raw_password):
        
        if not self.password:
            return False
        password_stripped = self.password.strip()
        if password_stripped.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            try:
                return django_check_password(raw_password, password_stripped)
            except:
                return False
        else:
            return password_stripped == raw_password

    def set_password(self, raw_password):
       
        self.password = raw_password
        self._password = raw_password


    def atualizar_senha(self, nova_senha):
       
        from .utils import atualizar_senha
        return atualizar_senha(self.usua_nome, nova_senha)

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return True  # ou coloque uma lógica se quiser restringir

    @property
    def is_superuser(self):
        return True  # idem, pode colocar regra

    @property
    def is_active(self):
        return True

    @property
    def last_login(self):
        return None
    
    @property
    def setor(self):
        from OrdemdeServico.models import OrdemServicoFaseSetor 
        try:
            return OrdemServicoFaseSetor.objects.get(osfs_codi=self.usua_seto)
        except OrdemServicoFaseSetor.DoesNotExist:
            return None

# ---- Classes auxiliares ----

class Empresas(models.Model):
    empr_codi = models.AutoField(primary_key=True, db_column='empr_codi')
    empr_nome = models.CharField('Nome da Empresa', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ', max_length=14, unique=True, db_column='empr_cnpj')

    class Meta:
        db_table = 'empresas'
        managed = False

    def __str__(self):
        return self.empr_nome


class Filiais(models.Model):
    empr_empr = models.IntegerField(primary_key=True, db_column='empr_empr')
    empr_codi = models.IntegerField(db_column='empr_codi')
    empr_nome = models.CharField('Nome da Filial', max_length=100, db_column='empr_nome')
    empr_docu = models.CharField('CNPJ da Filial', max_length=14, unique=True, db_column='empr_cnpj')
    empr_fant = models.CharField('Nome Fantasia', max_length=100, db_column='empr_fant')    
    empr_insc_esta = models.CharField(max_length=30, blank=True, null=True)
    empr_insc_muni = models.CharField(max_length=30, blank=True, null=True)
    empr_sufr = models.CharField(max_length=30, blank=True, null=True)
    empr_cei = models.CharField(max_length=12, blank=True, null=True)
    empr_nire = models.CharField(max_length=30, blank=True, null=True)
    empr_data_nire = models.DateField(blank=True, null=True)
    empr_cnae = models.CharField(max_length=8, blank=True, null=True)
    empr_cae = models.CharField(max_length=30, blank=True, null=True)
    empr_natu_juri = models.CharField(max_length=30, blank=True, null=True)
    empr_regi = models.CharField(max_length=60, blank=True, null=True)
    empr_data_regi = models.DateField(blank=True, null=True)
    empr_regi_junt = models.CharField(max_length=30, blank=True, null=True)
    empr_regi_outr = models.CharField(max_length=30, blank=True, null=True)
    empr_regi_trib = models.CharField(max_length=1, blank=True, null=True, choices= (('1', 'Simples Nacional'), ('2', 'Simples com Excesso de Limite'), ('3', 'Regime Normal')), default='1')
    empr_cep = models.CharField(max_length=8, blank=True, null=True)
    empr_ende = models.CharField(max_length=60, blank=True, null=True)
    empr_nume = models.CharField(max_length=10, blank=True, null=True)
    empr_comp = models.CharField(max_length=20, blank=True, null=True)
    empr_bair = models.CharField(max_length=60, blank=True, null=True)
    empr_cida = models.CharField(max_length=60, blank=True, null=True)
    empr_esta = models.CharField(max_length=2, blank=True, null=True)
    empr_pais = models.CharField(max_length=60, blank=True, null=True)
    empr_fone = models.CharField(max_length=14, blank=True, null=True)
    empr_resp = models.CharField(max_length=60, blank=True, null=True)
    empr_celu = models.CharField(max_length=14, blank=True, null=True)
    empr_emai = models.CharField(max_length=100, blank=True, null=True)
    empr_emai_empr = models.CharField(max_length=100, blank=True, null=True)
    empr_pagi = models.CharField(max_length=100, blank=True, null=True)
    empr_codi_cont = models.IntegerField(blank=True, null=True)
    empr_codi_soci = models.IntegerField(blank=True, null=True)
    empr_obse = models.TextField(blank=True, null=True)
    empr_codi_cida = models.CharField(max_length=7, blank=True, null=True)
    empr_codi_esta = models.CharField(max_length=2, blank=True, null=True)
    empr_codi_pais = models.CharField(max_length=6, blank=True, null=True)
    empr_cpf = models.CharField(max_length=11, blank=True, null=True)
    empr_nit = models.CharField(max_length=11, blank=True, null=True)
    empr_logo = models.BinaryField(blank=True, null=True)
    empr_teso = models.IntegerField(blank=True, null=True)
    empr_prox_host = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_senh = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_port = models.CharField(max_length=10, blank=True, null=True)
    empr_prox_usua = models.CharField(max_length=100, blank=True, null=True)
    empr_ambi_nfe = models.CharField(max_length=1, blank=True, null=True, choices= (('1', 'Produção'), ('2', 'Homologação')), default='1')
    empr_cert = models.CharField(max_length=100, blank=True, null=True)
    empr_senh_cert = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_host = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_port = models.CharField(max_length=10, blank=True, null=True)
    empr_smtp_usua = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_senh = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_emai = models.CharField(max_length=100, blank=True, null=True)
    empr_cone_segu = models.BooleanField(blank=True, null=True)
    empr_ssl = models.BooleanField(blank=True, null=True)
    empr_tls = models.BooleanField(blank=True, null=True)
    empr_seri_cert_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_senh_cert_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_ambi_cte = models.IntegerField(blank=True, null=True)
    empr_prox_host_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_port_cte = models.CharField(max_length=10, blank=True, null=True)
    empr_prox_user_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_pass_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_lote_cte = models.IntegerField(blank=True, null=True)
    empr_lote_nfe = models.IntegerField(blank=True, null=True)
    empr_smtp_host_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_port_cte = models.CharField(max_length=10, blank=True, null=True)
    empr_smtp_usua_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_senh_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_smtp_emai_cte = models.CharField(max_length=100, blank=True, null=True)
    empr_cone_segu_cte = models.BooleanField(blank=True, null=True)
    empr_ssl_cte = models.BooleanField(blank=True, null=True)
    empr_tls_cte = models.BooleanField(blank=True, null=True)
    
    empr_lote_even_nfe = models.IntegerField(blank=True, null=True)
    empr_lote_even_cte = models.IntegerField(blank=True, null=True)
    empr_apur_ipi = models.CharField(max_length=1, blank=True, null=True)
    empr_lote_cart_corr = models.IntegerField(blank=True, null=True)
    empr_prox_host_nfs = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_senh_nfs = models.CharField(max_length=100, blank=True, null=True)
    empr_prox_port_nfs = models.CharField(max_length=10, blank=True, null=True)
    empr_prox_usua_nfs = models.CharField(max_length=100, blank=True, null=True)
    empr_ambi_nfe_nfs = models.CharField(max_length=1, blank=True, null=True)
    empr_cert_nfs = models.CharField(max_length=100, blank=True, null=True)
    empr_senh_cert_nfs = models.CharField(max_length=100, blank=True, null=True)
    empr_rps = models.IntegerField(blank=True, null=True)
    empr_lote_nfes = models.IntegerField(blank=True, null=True)
    empr_seri_nfes = models.CharField(max_length=15, blank=True, null=True)
    empr_regi_trib_serv = models.IntegerField(blank=True, null=True)
    empr_simp_naci_serv = models.IntegerField(blank=True, null=True)
    empr_ince_cult = models.BooleanField(blank=True, null=True)
    empr_temp_resp_nfs = models.IntegerField(blank=True, null=True)
    empr_codi_serv = models.CharField(max_length=20, blank=True, null=True)
    empr_exig_iss = models.IntegerField(blank=True, null=True)
    empr_nume_proc = models.CharField(max_length=50, blank=True, null=True)
    empr_logo_pref = models.BinaryField(blank=True, null=True)
    empr_desc_serv = models.TextField(blank=True, null=True)
    empr_nume_cafr = models.IntegerField(blank=True, null=True)
    empr_perf_sped = models.CharField(max_length=1, blank=True, null=True)
    empr_ativ_sped = models.CharField(max_length=1, blank=True, null=True)
    empr_nsu = models.CharField(max_length=50, blank=True, null=True)
    empr_logo_2 = models.BinaryField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    empr_mdf_cte = models.IntegerField(blank=True, null=True)
    empr_mdf_nfe = models.IntegerField(blank=True, null=True)
    empr_cte_esta = models.BooleanField(blank=True, null=True)
    empr_cabe_empr = models.TextField(blank=True, null=True)
    empr_tipo_empr_ecd = models.CharField(max_length=6, blank=True, null=True)
    empr_id_toke = models.CharField(max_length=30, blank=True, null=True)
    empr_csn_toke = models.CharField(max_length=50, blank=True, null=True)
    empr_ambi_nfec = models.CharField(max_length=1, blank=True, null=True, choices= (('1', 'Produção'), ('2', 'Homologação')), default='1')
    empr_tipo_tran_nfec = models.IntegerField(blank=True, null=True)
    empr_danf_pais = models.BooleanField(blank=True, null=True)
    empr_senh_elot = models.CharField(max_length=30, blank=True, null=True)
    empr_cert_digi = models.BinaryField(blank=True, null=True)



    class Meta:
        db_table = 'filiais'
        managed = False

    def __str__(self):
        return self.empr_nome
    
    @property
    def empresa(self):
        try:
            return Empresas.objects.get(empr_codi=self.empr_empr)
        except Empresas.DoesNotExist:
            return None



class Licencas(models.Model):
    lice_id = models.AutoField(primary_key=True)
    lice_docu = models.CharField(max_length=14, unique=True)
    lice_nome = models.CharField(max_length=100)
    lice_emai = models.EmailField(blank=True, null=True)
    lice_bloq = models.BooleanField(default=False)
    lice_nume_empr = models.IntegerField()
    lice_nume_fili = models.IntegerField()
    #lice_modu_libe = models.TextField(default="{}")
    _log_data = models.DateField(blank=True, null=True) 
    _log_time = models.TimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'licencas'

    def get_modu_libe(self):
        return json.loads(self.lice_modu_libe or "{}")

    def set_modu_libe(self, data):
        self.lice_modu_libe = json.dumps(data)
    
    


class Liberar(models.Model):
    libe_usua = models.IntegerField(primary_key=True)
    libe_desc_vend = models.BooleanField(blank=True, null=True)
    libe_cred = models.BooleanField(blank=True, null=True)
    libe_clie_bloq = models.BooleanField(blank=True, null=True)
    libe_tabe_prec = models.BooleanField(blank=True, null=True)
    libe_manu_os_fina = models.BooleanField(blank=True, null=True)
    libe_impo_fina_xml = models.BooleanField(blank=True, null=True)
    libe_nao_fina_xml = models.BooleanField(blank=True, null=True)
    libe_impr_pedi_40 = models.BooleanField(blank=True, null=True)
    libe_alte_unit_pedi = models.BooleanField(blank=True, null=True)
    libe_canc_cte_repo = models.BooleanField(blank=True, null=True)
    field_log_data = models.DateField(db_column='_log_data', blank=True, null=True)  # Field renamed because it started with '_'.
    field_log_time = models.TimeField(db_column='_log_time', blank=True, null=True)  # Field renamed because it started with '_'.
    libe_codi_vend = models.IntegerField(blank=True, null=True)
    libe_rece_outr = models.BooleanField(blank=True, null=True)
    libe_paga_outr = models.BooleanField(blank=True, null=True)
    libe_fina_vend_tipo_outr = models.BooleanField(blank=True, null=True)
    libe_alte_cart_fret = models.BooleanField(blank=True, null=True)
    libe_posi_atal = models.IntegerField(blank=True, null=True)
    libe_cont_tota_tele_vend = models.BooleanField(blank=True, null=True)
    libe_alte_cada_tele_vend = models.BooleanField(blank=True, null=True)
    libe_impr_pedi_proc = models.BooleanField(blank=True, null=True)
    libe_grup_sugr = models.BooleanField(blank=True, null=True)
    libe_manu_pedi_comp = models.BooleanField(blank=True, null=True)
    libe_manu_pedi_vend = models.BooleanField(blank=True, null=True)
    libe_perm_ver_cust_rel_vend = models.BooleanField(blank=True, null=True)
    libe_conf_fatu_pedi = models.BooleanField(blank=True, null=True)
    libe_fina_os_fina = models.BooleanField(blank=True, null=True)
    libe_assi_digi = models.CharField(max_length=40, blank=True, null=True)
    libe_mult = models.BooleanField(blank=True, null=True)
    libe_assi_comp = models.BooleanField(blank=True, null=True)
    libe_modi_fina_pedi = models.BooleanField(blank=True, null=True)
    libe_modi_mens_padr_pedi = models.BooleanField(blank=True, null=True)
    libe_alte_sele_prod = models.BooleanField(blank=True, null=True)
    libe_devo_vend_30 = models.BooleanField(blank=True, null=True)
    libe_assi_libe_nota = models.BooleanField(blank=True, null=True)
    libe_depa_pess = models.BooleanField(blank=True, null=True)
    libe_muda_stat_fatu_aber = models.BooleanField(blank=True, null=True)
    libe_prec_comp_posi_esto = models.BooleanField(blank=True, null=True)
    libe_vend_caix = models.BooleanField(blank=True, null=True)
    libe_rece_aler_troc = models.BooleanField(blank=True, null=True)
    libe_reab_orpr_joia = models.BooleanField(blank=True, null=True)
    limp_limp_imag = models.BooleanField(blank=True, null=True)
    libe_nfce_todo_usua = models.BooleanField(blank=True, null=True)
    bloq_alte_vend_clie = models.BooleanField(blank=True, null=True)
    bloq_alte_vend_pedi = models.BooleanField(blank=True, null=True)
    libe_prot_sera_enti = models.BooleanField(blank=True, null=True)
    libe_impr_os_40 = models.BooleanField(blank=True, null=True)
    excl_toda_peca_serv = models.BooleanField(blank=True, null=True)
    lanc_os_cmal_gara = models.BooleanField(blank=True, null=True)
    pedi_vend_some_semf = models.BooleanField(blank=True, null=True)
    alte_data_prox_venc_fatu = models.BooleanField(blank=True, null=True)
    libe_reab_caix_diar = models.BooleanField(blank=True, null=True)
    libe_alte_data_rece = models.BooleanField(blank=True, null=True)
    libe_bloq_alte_valo_unit = models.BooleanField(blank=True, null=True)
    libe_canc_vend_caix = models.BooleanField(blank=True, null=True)
    libe_perm_visu_cust_orca = models.BooleanField(blank=True, null=True)
    libe_impr_pedi_40_anti = models.BooleanField(blank=True, null=True)
    libe_enti_outr = models.BooleanField(blank=True, null=True)
    libe_alte_pedi_proc = models.BooleanField(blank=True, null=True)
    libe_alte_tecn_os = models.BooleanField(blank=True, null=True)
    libe_perm_visu_cust_pedi = models.BooleanField(blank=True, null=True)
    libe_rela_inve = models.BooleanField(blank=True, null=True)
    libe_perm_desv_titu_reme = models.BooleanField(blank=True, null=True)
    nao_perm_aces_aba_bloq = models.BooleanField(blank=True, null=True)
    libe_visu_prcu_cons_prod = models.BooleanField(blank=True, null=True)
    nao_perm_visu_valo_os = models.BooleanField(blank=True, null=True)
    marc_enti_nunc_bloq = models.BooleanField(blank=True, null=True)
    libe_agri_movi_esto = models.BooleanField(blank=True, null=True)
    libe_agri_entr_esto_unit_zero = models.BooleanField(blank=True, null=True)
    libe_agri_nao_alte_unit = models.BooleanField(blank=True, null=True)
    libe_agri_perm_cecu = models.BooleanField(blank=True, null=True)
    libe_enti_func_vend = models.BooleanField(blank=True, null=True)
    libe_cfop_desc_usua = models.BooleanField(blank=True, null=True)
    libe_caix_form_dinh = models.BooleanField(blank=True, null=True)
    libe_caix_form_cart = models.BooleanField(blank=True, null=True)
    libe_caix_form_pix = models.BooleanField(blank=True, null=True)
    libe_caix_form_cred = models.BooleanField(blank=True, null=True)
    libe_caix_form_cheq = models.BooleanField(blank=True, null=True)
    libe_agri_clau_os = models.BooleanField(blank=True, null=True)
    libe_edit_fina_os_enti = models.BooleanField(blank=True, null=True)
    libe_maxi_form = models.BooleanField(blank=True, null=True)
    libe_atua_cust_agri = models.BooleanField(blank=True, null=True)
    libe_atua_esto = models.BooleanField(blank=True, null=True)
    libe_cust_orca_piso = models.BooleanField(blank=True, null=True)
    bloq_filt_cons_prod = models.BooleanField(blank=True, null=True)
    libe_libe_orca_vend = models.BooleanField(blank=True, null=True)
    nao_visu_orca = models.BooleanField(blank=True, null=True)
    libe_libe_pedi_comp = models.BooleanField(blank=True, null=True)
    libe_codi_gere = models.IntegerField(blank=True, null=True)
    libe_tecn_os = models.BooleanField(blank=True, null=True)
    libe_esca_nfe = models.IntegerField(blank=True, null=True)
    #libe_alte_cheq = models.BooleanField(blank=True, null=True)
    #libe_reme = models.BooleanField(blank=True, null=True)
    #libe_alte_peca_os = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'liberar'
