

class ParametrosAgricolasRegistry:

    PARAMS = {
        "controla_estoque": {
            "tipo": bool,
            "default": True,
            "label": "Controla estoque",
            "grupo": "Estoque",
        },
        "permite_estoque_negativo": {
            "tipo": bool,
            "default": False,
            "label": "Permite estoque negativo",
            "grupo": "Estoque",
        },
        "controla_lote": {
            "tipo": bool,
            "default": False,
            "label": "Controla estoque por lote",
            "grupo": "Estoque",
        },
        "cadastros_unificados_entidades": {
            "tipo": bool,
            "default": False,
            "label": "Cadastros unificados entidades",
            "grupo": "Cadastros",
        },
        "cadastros_unificados_produtos": {
            "tipo": bool,
            "default": False,
            "label": "Cadastros unificados produtos",
            "grupo": "Cadastros",
        },
        "movimentacao_gera_financeiro": {
            "tipo": bool,
            "default": False,
            "label": "Movimentação gera financeiro",
            "grupo": "Financeiro",
        },
    }