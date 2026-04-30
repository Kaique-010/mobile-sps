from Pisos.models import Orcamentopisos, Pedidospisos, Itensorcapisos, Itenspedidospisos


class OrcamentoExportarPedidoService:

    def executar(self, *, banco, empresa, filial, numero):
        orcamento = Orcamentopisos.objects.using(banco).get(
            orca_empr=empresa,
            orca_fili=filial,
            orca_nume=numero,
        )

        if orcamento.orca_stat == 2:
            raise ValueError("Orçamento já exportado")

        ultimo = (
            Pedidospisos.objects.using(banco)
            .filter(pedi_empr=empresa, pedi_fili=filial)
            .order_by("-pedi_nume")
            .first()
        )

        proximo = (ultimo.pedi_nume + 1) if ultimo else 1

        pedido = Pedidospisos.objects.using(banco).create(
            pedi_empr=orcamento.orca_empr,
            pedi_fili=orcamento.orca_fili,
            pedi_nume=proximo,
            pedi_clie=orcamento.orca_clie,
            pedi_data=orcamento.orca_data,
            pedi_tota=orcamento.orca_tota,
            pedi_obse=orcamento.orca_obse,
            pedi_vend=orcamento.orca_vend,
            pedi_desc=orcamento.orca_desc,
            pedi_fret=orcamento.orca_fret,
            pedi_ende=orcamento.orca_ende,
            pedi_nume_ende=orcamento.orca_nume_ende,
            pedi_comp=orcamento.orca_comp,
            pedi_bair=orcamento.orca_bair,
            pedi_cida=orcamento.orca_cida,
            pedi_esta=orcamento.orca_esta,
            pedi_orca=orcamento.orca_nume,
            pedi_mode_piso=orcamento.orca_mode_piso,
            pedi_mode_alum=orcamento.orca_mode_alum,
            pedi_mode_roda=orcamento.orca_mode_roda,
            pedi_mode_port=orcamento.orca_mode_port,
            pedi_mode_outr=orcamento.orca_mode_outr,
            pedi_sent_piso=orcamento.orca_sent_piso,
            pedi_ajus_port=orcamento.orca_ajus_port,
            pedi_degr_esca=orcamento.orca_degr_esca,
            pedi_obra_habi=orcamento.orca_obra_habi,
            pedi_movi_mobi=orcamento.orca_movi_mobi,
            pedi_remo_roda=orcamento.orca_remo_roda,
            pedi_remo_carp=orcamento.orca_remo_carp,
            pedi_croq_info=orcamento.orca_croq_info,
            pedi_stat=0,
        )

        itens = Itensorcapisos.objects.using(banco).filter(
            item_empr=empresa,
            item_fili=filial,
            item_orca=numero,
        )

        for item in itens:
            Itenspedidospisos.objects.using(banco).create(
                item_empr=pedido.pedi_empr,
                item_fili=pedido.pedi_fili,
                item_pedi=pedido.pedi_nume,
                item_ambi=item.item_ambi,
                item_prod=item.item_prod,
                item_m2=item.item_m2,
                item_quan=item.item_quan,
                item_unit=item.item_unit,
                item_suto=item.item_suto,
                item_obse=item.item_obse,
                item_nome_ambi=item.item_nome_ambi,
                item_nume=item.item_nume,
                item_caix=item.item_caix,
                item_desc=item.item_desc,
                item_queb=item.item_queb,
            )

        orcamento.orca_stat = 2
        orcamento.orca_pedi = pedido.pedi_nume
        orcamento.save(using=banco)

        return pedido.pedi_nume