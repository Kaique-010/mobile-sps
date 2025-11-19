from Entidades.models import Entidades
from Licencas.models import Filiais
from Produtos.models import Produtos
from Notas_Fiscais.models import Nota, NotaItem, NotaItemImposto, Transporte
from Notas_Fiscais.legacy_migration.transformers import NotaTransformer

class NotaWriter:

    @staticmethod
    def buscar_emitente(empresa, filial, banco):
        return Filiais.objects.using(banco).get(
            empr_empr=empresa,
            empr_codi=filial
        )

    @staticmethod
    def buscar_destinatario(codigo_destinatario, empresa, banco):
        return Entidades.objects.using(banco).get(
            enti_empr=empresa,
            enti_clie=codigo_destinatario
        )

    @staticmethod
    def salvar_nota(data, emitente, destinatario, *, banco: str, dry_run: bool = False):
        preview = f"Nota {data['empresa']}/{data['filial']} mod {data['modelo']} série {data['serie']} nº {data['numero']}"

        if dry_run:
            return {"nota": preview, "msg": "[DRY] Nota não persistida", "obj": None}

        nota, created = Nota.objects.using(banco).get_or_create(
            empresa=data["empresa"],
            filial=data["filial"],
            modelo=data["modelo"],
            serie=data["serie"],
            numero=data["numero"],
            defaults={
                **{k: v for k, v in data.items() if k not in {"emitente", "destinatario"}},
                "emitente": emitente,
                "destinatario": destinatario,
            },
        )

        msg = "Nota criada" if created else "Nota já existia"
        return {"nota": preview, "msg": msg, "obj": nota}

    @staticmethod
    def salvar_itens_e_impostos(nota, itens_rows, *, banco: str):
        NotaItem.objects.using(banco).filter(nota=nota).delete()
        for row in itens_rows:
            item_data = NotaTransformer.item(row)
            produto = Produtos.objects.using(banco).filter(prod_codi=item_data["produto_codigo"]).first()
            if not produto:
                continue
            item_obj = NotaItem.objects.using(banco).create(
                nota=nota,
                produto=produto,
                quantidade=item_data["quantidade"],
                unitario=item_data["unitario"],
                desconto=item_data["desconto"],
                cfop=item_data["cfop"][:4],
                ncm=item_data["ncm"][:8],
                cest=(item_data["cest"] or "")[:7],
                cst_icms=str(item_data["cst_icms"] or "")[:3],
                cst_pis=str(item_data["cst_pis"] or "")[:2],
                cst_cofins=str(item_data["cst_cofins"] or "")[:2],
                total=item_data["total"],
            )
            imp_data = NotaTransformer.imposto(row)
            NotaItemImposto.objects.using(banco).update_or_create(
                item=item_obj,
                defaults={
                    "icms_base": imp_data["icms_base"],
                    "icms_aliquota": imp_data["icms_aliquota"],
                    "icms_valor": imp_data["icms_valor"],
                    "ipi_valor": imp_data["ipi_valor"],
                    "pis_valor": imp_data["pis_valor"],
                    "cofins_valor": imp_data["cofins_valor"],
                    "fcp_valor": imp_data["fcp_valor"],
                    "ibs_base": imp_data["ibs_base"],
                    "ibs_aliquota": imp_data["ibs_aliquota"],
                    "ibs_valor": imp_data["ibs_valor"],
                    "cbs_base": imp_data["cbs_base"],
                    "cbs_aliquota": imp_data["cbs_aliquota"],
                    "cbs_valor": imp_data["cbs_valor"],
                },
            )

    @staticmethod
    def definir_transporte(nota, raw, *, banco: str):
        modalidade = raw.get("x02_modfrete") or 0
        transportadora_id = raw.get("transportadora")
        placa = raw.get("x19_placa_veic")
        uf = raw.get("x20_uf_veic")

        ent = None
        if transportadora_id:
            ent = Entidades.objects.using(banco).filter(enti_empr=raw.get("empresa"), enti_clie=transportadora_id).first()
        if not ent:
            cnpj = raw.get("x04_cnpj_transp")
            if cnpj:
                ent = Entidades.objects.using(banco).filter(enti_cnpj=cnpj).first()

        Transporte.objects.using(banco).update_or_create(
            nota=nota,
            defaults={
                "modalidade_frete": modalidade,
                "transportadora": ent,
                "placa_veiculo": placa,
                "uf_veiculo": uf,
            },
        )