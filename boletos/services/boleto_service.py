from ..adaptadores.itau.itau_boleto_adapter import ItauBoletoAdapter
from ..adaptadores.bradesco.bradesco_boleto_adapter import BradescoBoletoAdapter
from ..adaptadores.caixa.caixa_boleto_adapter import CaixaBoletoAdapter
from ..adaptadores.sicoob.sicoob_boleto_adapter import SicoobBoletoAdapter
from ..adaptadores.sicredi.sicredi_boleto_adapter import SicrediBoletoAdapter


class BoletoService:
    def gerar_pdf(self, titulo, cedente, sacado, banco_cfg, caminho):
        adapter = self.resolver_adapter(banco_cfg)
        return adapter.gerar_pdf(titulo, cedente, sacado, banco_cfg, caminho)

    def resolver_adapter(self, banco_cfg):
        codigo = str(banco_cfg.get("codigo_banco"))
        if codigo == "341":
            return ItauBoletoAdapter()
        if codigo == "237":
            return BradescoBoletoAdapter()
        if codigo == "104":
            return CaixaBoletoAdapter()
        if codigo == "756":
            return SicoobBoletoAdapter()
        if codigo == "748":
            return SicrediBoletoAdapter()
        return ItauBoletoAdapter()

    def banco_cfg_from_entidade(self, banco_alias, empresa_id, entidade_id, logo_variation="Colorido"):
        from Entidades.models import Entidades
        e = Entidades.objects.using(banco_alias).filter(enti_empr=str(empresa_id), enti_clie=str(entidade_id)).only(
            'enti_banc','enti_agen','enti_diag','enti_coco','enti_dico','enti_care'
        ).first()
        if not e:
            raise Exception("Entidade não encontrada para configuração bancária")
        return {
            'codigo_banco': str(e.enti_banc or ''),
            'agencia': str(e.enti_agen or ''),
            'dv_agencia': str(e.enti_diag or ''),
            'conta': str(e.enti_coco or ''),
            'dv': str(e.enti_dico or ''),
            'carteira': str(e.enti_care or ''),
            'logo_variation': logo_variation,
        }
