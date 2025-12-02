from django.views import View
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from core.utils import get_licenca_db_config
import logging

from ...models import PedidoVenda
from Notas_Fiscais.emissao.emissao_nota_service import EmissaoNotaService


class PedidoEmitirNFeView(View):

    def get(self, request, slug, pk):
        banco = get_licenca_db_config(request) or "default"
        empresa_id = request.session.get('empresa_id', 1)
        filial_id = request.session.get('filial_id', 1)

        pedido = get_object_or_404(
            PedidoVenda.objects.using(banco).filter(
                pedi_empr=int(empresa_id),
                pedi_fili=int(filial_id)
            ),
            pedi_nume=int(pk)
        )

        try:
            # 1) Montar dados mínimos da Nota a partir do Pedido
            cliente = pedido.cliente
            if not cliente:
                raise Exception("Cliente não encontrado no pedido.")

            # Itens
            itens = []
            for item in pedido.itens:
                prod = item.produto
                if not prod:
                    raise Exception(f"Produto {item.iped_prod} não encontrado.")

                # CFOP padrão por tipo de operação
                tipo = pedido.pedi_tipo_oper
                if tipo == "DEVOLUCAO_VENDA":
                    cfop = "1202"
                elif tipo == "BONIFICACAO":
                    cfop = "5910"
                elif tipo == "REMESSA":
                    cfop = "5915"
                elif tipo == "TRANSFERENCIA":
                    cfop = "5152"
                else:
                    cfop = "5102"

                try:
                    prod_id = int(item.iped_prod)
                except Exception:
                    raise Exception(f"Produto inválido no item: {item.iped_prod}")

                itens.append({
                    "produto": prod_id,
                    "quantidade": float(item.iped_quan or 0),
                    "unitario": float(item.iped_unit or 0),
                    "desconto": float(item.iped_desc or 0),
                    "cfop": cfop,
                    "ncm": prod.prod_ncm,
                    "cest": None,
                    "cst_icms": "000",
                    "cst_pis": "01",
                    "cst_cofins": "01",
                })

            # Mapear forma de pagamento do pedido para tPag SEFAZ
            forma = str(pedido.pedi_form_rece or "54")
            mapa_tpag = {
                "54": "01",  # Dinheiro
                "50": "02",  # Cheque pré → Cheque
                "01": "02",  # Cheque
                "51": "03",  # Cartão de Crédito
                "52": "04",  # Cartão de Débito
                "55": "16",  # Depósito em conta
                "53": "15",  # Boleto bancário
                "60": "17",  # PIX
                "56": "01",  # Venda à vista → Dinheiro
            }
            tpag = mapa_tpag.get(forma, "01")

            # Dados da nota
            nota_data = {
                "modelo": "55",
                "serie": "1",
                "numero": 0,
                "data_emissao": str(pedido.pedi_data),
                "data_saida": None,
                "tipo_operacao": 1,
                "finalidade": 1,
                "ambiente": 2,
                "destinatario": cliente.enti_clie,
                "itens": itens,
                "tpag": tpag,
            }

            # 2) Emitir NF-e
            resultado = EmissaoNotaService.emitir_nota(
                dto_dict=nota_data,
                empresa=pedido.pedi_empr,
                filial=pedido.pedi_fili,
                database=banco
            )
            logging.getLogger(__name__).info(f"Resultado da NF-e: {resultado}")

            sefaz = resultado["sefaz"]

            if sefaz["status"] == "100":
                messages.success(
                    request,
                    f"NF-e autorizada com sucesso! Chave: {sefaz['chave']}"
                )
            else:
                messages.warning(
                    request,
                    f"Rejeição: {sefaz['status']} - {sefaz['motivo']}"
                )

        except Exception as e:
            messages.error(request, f"Erro ao emitir NF-e: {str(e)}")

        return redirect(f"/web/{slug}/pedidos/")
