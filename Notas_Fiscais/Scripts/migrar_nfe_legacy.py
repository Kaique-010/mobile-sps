from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from django.core.management import call_command
from django.db import connections

from core.utils import get_db_from_slug

# Deferir imports de modelos Django para após django.setup()
NotaFiscal = None
Infvv = None
Nota = None
NotaItem = None
NotaItemImposto = None
Transporte = None
Entidades = None
Filiais = None
Produtos = None


def _resolve_emitente(nota_leg, database):
    doc = nota_leg.emitente_cnpj or nota_leg.emitente_cpf
    if not doc:
        return None
    return Filiais.objects.using(database).filter(empr_docu=doc).first()


def _resolve_entidade(cnpj, cpf, database, empresa=None):
    if not cnpj and not cpf:
        return None
    qs = Entidades.objects.using(database)
    if empresa:
        qs = qs.filter(enti_empr=empresa)
    if cnpj:
        obj = qs.filter(enti_cnpj=cnpj).first()
        if obj:
            return obj
    if cpf:
        obj = qs.filter(enti_cpf=cpf).first()
        if obj:
            return obj
    return None


def _resolve_transportadora(nota_leg, database, empresa=None):
    return _resolve_entidade(nota_leg.transportador_cnpj, nota_leg.transportador_cpf, database, empresa)


def _resolve_produto(codigo, database, empresa=None):
    if not codigo:
        return None
    qs = Produtos.objects.using(database).filter(prod_codi=str(codigo))
    if empresa:
        qs = qs.filter(prod_empr=empresa)
    return qs.first()


def _map_status(nota_leg):
    if nota_leg.cancelada:
        return 200
    if nota_leg.protocolo_nfe:
        return 100
    return 0


@transaction.atomic
def migrar_nota(nota_leg, database="default"):
    empresa = nota_leg.empresa or 0
    filial = nota_leg.filial or 0

    emitente = _resolve_emitente(nota_leg, database)
    destinatario = _resolve_entidade(nota_leg.destinatario_cnpj, nota_leg.destinatario_cpf, database, empresa)

    if not emitente or not destinatario or not empresa or not filial or not nota_leg.numero_nota_fiscal:
        return None

    payload = {
        "empresa": int(empresa),
        "filial": int(filial),
        "modelo": nota_leg.modelo or "55",
        "serie": nota_leg.serie or "1",
        "numero": int(nota_leg.numero_nota_fiscal),
        "data_emissao": nota_leg.data_emissao or nota_leg.data_saida_entrada,
        "data_saida": nota_leg.data_saida_entrada,
        "tipo_operacao": int(nota_leg.tipo_operacao or 1),
        "finalidade": int(nota_leg.finalidade_emissao or 1),
        "ambiente": int(nota_leg.ambiente or 2),
        "emitente": emitente,
        "destinatario": destinatario,
        "status": _map_status(nota_leg),
        "chave_acesso": nota_leg.chave_acesso,
        "protocolo_autorizacao": nota_leg.protocolo_nfe,
        "xml_autorizado": nota_leg.xml_nfe,
    }

    nota = Nota.objects.using(database).create(**payload)

    itens_leg = Infvv.objects.using(database).filter(id=nota_leg.id).order_by("nitem")
    for it in itens_leg:
        prod = _resolve_produto(it.i02_cprod, database, empresa)
        if not prod or not it.i10_qcom:
            continue

        qtd = Decimal(it.i10_qcom or 0)
        unit = Decimal(it.i10a_vuncom or 0)
        desc = Decimal(it.i17_vdesc or 0)
        total = Decimal(it.i11_vprod or (qtd * unit - desc))

        item = NotaItem.objects.using(database).create(
            nota=nota,
            produto=prod,
            quantidade=qtd,
            unitario=unit,
            desconto=desc,
            cfop=str(it.i08_cfop or ""),
            ncm=str(it.i05_ncm or ""),
            cest=None,
            cst_icms=str(it.n12 or "00"),
            cst_pis="01",
            cst_cofins="01",
            total=total,
        )

        NotaItemImposto.objects.using(database).create(
            item=item,
            icms_base=it.n15_vbc,
            icms_aliquota=it.n16_picms,
            icms_valor=it.n17_vicms,
            ipi_valor=None,
            pis_valor=None,
            cofins_valor=None,
            fcp_valor=None,
            ibs_base=None,
            ibs_aliquota=None,
            ibs_valor=None,
            cbs_base=None,
            cbs_aliquota=None,
            cbs_valor=None,
        )

    transp = {
        "modalidade_frete": int(nota_leg.modalidade_frete or 9),
        "transportadora": _resolve_transportadora(nota_leg, database, empresa),
        "placa_veiculo": nota_leg.veiculo_placa,
        "uf_veiculo": nota_leg.veiculo_uf,
    }
    Transporte.objects.using(database).update_or_create(
        nota=nota,
        defaults=transp,
    )

    return nota


def migrar(database="default", empresa=None, filial=None, limit=None):
    qs = NotaFiscal.objects.using(database).all()
    if empresa:
        qs = qs.filter(empresa=empresa)
    if filial:
        qs = qs.filter(filial=filial)
    if limit:
        qs = qs[:int(limit)]

    criado = 0
    pulado = 0
    for nf in qs:
        try:
            obj = migrar_nota(nf, database)
            if obj:
                criado += 1
            else:
                pulado += 1
        except Exception:
            pulado += 1
            continue

    return {"criadas": criado, "puladas": pulado}


def criar_tabelas(database_alias="default"):
    try:
        conn = connections[database_alias]
        existing = set(conn.introspection.table_names())
        with conn.schema_editor() as editor:
            # Ordem importa para FKs
            for model in [Nota, NotaEvento, Transporte, NotaItem, NotaItemImposto]:
                table = model._meta.db_table
                if table not in existing:
                    editor.create_model(model)
        return True
    except Exception as e:
        print({"erro": str(e)})
        return False

if __name__ == "__main__":
    import os, django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    alias = os.environ.get("DB_ALIAS", "default")
    # Garante que o alias exista em settings.DATABASES (conexões dinâmicas por slug)
    try:
        get_db_from_slug(alias)
    except Exception:
        pass

    # Importar modelos após setup
    from ..legado_models import NotaFiscal as _NotaFiscal, Infvv as _Infvv
    from ..models import Nota as _Nota, NotaItem as _NotaItem, NotaItemImposto as _NotaItemImposto, Transporte as _Transporte, NotaEvento as _NotaEvento
    from Entidades.models import Entidades as _Entidades
    from Licencas.models import Filiais as _Filiais
    from Produtos.models import Produtos as _Produtos

    globals().update({
        'NotaFiscal': _NotaFiscal,
        'Infvv': _Infvv,
        'Nota': _Nota,
        'NotaItem': _NotaItem,
        'NotaItemImposto': _NotaItemImposto,
        'Transporte': _Transporte,
        'NotaEvento': _NotaEvento,
        'Entidades': _Entidades,
        'Filiais': _Filiais,
        'Produtos': _Produtos,
    })

    action = os.environ.get("ACTION") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if action in ["criar-tabelas", "create_tables", "criar", "tables"]:
        ok = criar_tabelas(database_alias=alias)
        print({"tabelas_criadas": ok, "database": alias})
    else:
        empresa = os.environ.get("EMPRESA_ID")
        filial = os.environ.get("FILIAL_ID")
        limit = os.environ.get("LIMIT")
        out = migrar(database=alias, empresa=empresa, filial=filial, limit=limit)
        print(out)