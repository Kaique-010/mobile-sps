from django.utils import timezone

from nfse.models import Nfse, NfseEvento, NfseItem


class PersistenciaNfseService:
    @staticmethod
    def criar_rascunho(context, data: dict):
        itens = data.pop('itens', []) or []

        nfse = Nfse.objects.using(context.db_alias).create(
            nfse_empr=context.empresa_id,
            nfse_fili=context.filial_id,

            nfse_statu='rascunho',
            nfse_muni_codi=data['municipio_codigo'],
            nfse_rps_nume=data['rps_numero'],
            nfse_rps_seri=data.get('rps_serie'),

            nfse_pres_doc=data['prestador_documento'],
            nfse_pres_nome=data['prestador_nome'],
            nfse_pres_muni_inci=data.get('municipio_incidencia'),

            nfse_tom_doc=data.get('tomador_documento'),
            nfse_tom_nome=data.get('tomador_nome'),
            nfse_tom_ie=data.get('tomador_ie'),
            nfse_tom_im=data.get('tomador_im'),
            nfse_tom_email=data.get('tomador_email'),
            nfse_tom_fone=data.get('tomador_telefone'),
            nfse_tom_ende=data.get('tomador_endereco'),
            nfse_tom_nume=data.get('tomador_numero'),
            nfse_tom_bair=data.get('tomador_bairro'),
            nfse_tom_cepe=data.get('tomador_cep'),
            nfse_tom_cida=data.get('tomador_cidade'),
            nfse_tom_esta=data.get('tomador_uf'),

            nfse_serv_codi=data['servico_codigo'],
            nfse_serv_desc=data['servico_descricao'],
            nfse_serv_cnae=data.get('cnae_codigo'),
            nfse_serv_lc116=data.get('lc116_codigo'),
            nfse_serv_muni=data.get('municipio_servico'),
            nfse_natu_oper=data.get('natureza_operacao'),

            nfse_val_serv=data.get('valor_servico') or 0,
            nfse_val_dedu=data.get('valor_deducao') or 0,
            nfse_val_desc=data.get('valor_desconto') or 0,
            nfse_val_inss=data.get('valor_inss') or 0,
            nfse_val_irrf=data.get('valor_irrf') or 0,
            nfse_val_csll=data.get('valor_csll') or 0,
            nfse_val_cofi=data.get('valor_cofins') or 0,
            nfse_val_pis=data.get('valor_pis') or 0,
            nfse_val_iss=data.get('valor_iss') or 0,
            nfse_val_liqu=data.get('valor_liquido') or data.get('valor_servico') or 0,
            nfse_aliq_iss=data.get('aliquota_iss') or 0,

            nfse_iss_ret=data.get('iss_retido', False),

            nfse_payl_envi={**data, 'itens': itens} if data else {'itens': itens},
            nfse_data_comp=data.get('data_competencia'),
        )

        if itens:
            objetos_itens = []
            for ordem, item in enumerate(itens, start=1):
                objetos_itens.append(
                    NfseItem(
                        nfsi_empr=context.empresa_id,
                        nfsi_fili=context.filial_id,
                        nfsi_nfse_id=nfse.pk,
                        nfsi_orde=ordem,
                        nfsi_desc=item['descricao'],
                        nfsi_qtde=item.get('quantidade') or 0,
                        nfsi_unit=item.get('valor_unitario') or 0,
                        nfsi_tota=item.get('valor_total') or 0,
                        nfsi_serv_codi=item.get('servico_codigo'),
                        nfsi_cnae=item.get('cnae_codigo'),
                        nfsi_lc116=item.get('lc116_codigo'),
                    )
                )

            NfseItem.objects.using(context.db_alias).bulk_create(objetos_itens)

        return nfse

    @staticmethod
    def salvar_envio(context, nfse: Nfse, payload: dict, xml_envio: str | None = None, status: str = 'processando'):
        nfse.nfse_payl_envi = payload
        nfse.nfse_statu = status

        if xml_envio:
            nfse.nfse_xml_envi = xml_envio

        nfse.save(using=context.db_alias)

    @staticmethod
    def marcar_processando(context, nfse: Nfse):
        nfse.nfse_statu = 'processando'
        nfse.save(using=context.db_alias)

    @staticmethod
    def marcar_emitida(context, nfse: Nfse, retorno: dict):
        nfse.nfse_statu = 'emitida'
        nfse.nfse_nume = retorno.get('numero') or nfse.nfse_nume
        nfse.nfse_codi_veri = retorno.get('codigo_verificacao') or nfse.nfse_codi_veri
        nfse.nfse_prot = retorno.get('protocolo') or nfse.nfse_prot
        nfse.nfse_res_envi = retorno
        nfse.nfse_xml_envi = retorno.get('xml_envio') or nfse.nfse_xml_envi
        nfse.nfse_xml_ret = retorno.get('xml_retorno')
        nfse.nfse_data_emis = retorno.get('data_emissao') or timezone.now()
        nfse.save(using=context.db_alias)

    @staticmethod
    def atualizar_consulta(context, nfse: Nfse, retorno: dict):
        status_retorno = (retorno.get('status') or '').lower()

        if status_retorno in ['emitida', 'autorizada']:
            nfse.nfse_statu = 'emitida'
        elif status_retorno in ['cancelada', 'cancelado']:
            nfse.nfse_statu = 'cancelada'

        nfse.nfse_nume = retorno.get('numero') or nfse.nfse_nume
        nfse.nfse_codi_veri = retorno.get('codigo_verificacao') or nfse.nfse_codi_veri
        nfse.nfse_prot = retorno.get('protocolo') or nfse.nfse_prot
        nfse.nfse_res_envi = retorno
        nfse.nfse_xml_envi = retorno.get('xml_envio') or nfse.nfse_xml_envi
        nfse.nfse_xml_ret = retorno.get('xml_retorno') or nfse.nfse_xml_ret

        if status_retorno in ['cancelada', 'cancelado'] and not nfse.nfse_data_canc:
            nfse.nfse_data_canc = timezone.now()

        nfse.save(using=context.db_alias)

    @staticmethod
    def marcar_erro(context, nfse: Nfse, erro, resposta=None, xml_retorno: str | None = None):
        nfse.nfse_statu = 'erro'
        nfse.nfse_mess_err = str(erro)

        if resposta is not None:
            nfse.nfse_res_envi = resposta

        if xml_retorno:
            nfse.nfse_xml_ret = xml_retorno

        nfse.save(using=context.db_alias)

    @staticmethod
    def marcar_cancelada(context, nfse: Nfse, resposta=None):
        nfse.nfse_statu = 'cancelada'
        nfse.nfse_data_canc = timezone.now()

        if resposta is not None:
            nfse.nfse_res_envi = resposta
            nfse.nfse_xml_envi = resposta.get('xml_envio') or nfse.nfse_xml_envi
            nfse.nfse_xml_ret = resposta.get('xml_retorno') or nfse.nfse_xml_ret

        nfse.save(using=context.db_alias)

    @staticmethod
    def obter_nfse(context, nfse_id: int):
        return (
            Nfse.objects.using(context.db_alias)
            .filter(
                nfse_id=nfse_id,
                nfse_empr=context.empresa_id,
                nfse_fili=context.filial_id,
            )
            .first()
        )

    @staticmethod
    def listar_itens(context, nfse_id: int):
        return (
            NfseItem.objects.using(context.db_alias)
            .filter(
                nfsi_nfse_id=nfse_id,
                nfsi_empr=context.empresa_id,
                nfsi_fili=context.filial_id,
            )
            .order_by('nfsi_orde', 'nfsi_id')
        )

    @staticmethod
    def registrar_evento(context, nfse_id: int, tipo: str, payload=None, resposta=None, descricao=None):
        return NfseEvento.objects.using(context.db_alias).create(
            nfsev_empr=context.empresa_id,
            nfsev_fili=context.filial_id,
            nfsev_nfse_id=nfse_id,
            nfsev_tip=tipo,
            nfsev_payl=payload,
            nfsev_ret=resposta,
            nfsev_desc=descricao,
        )