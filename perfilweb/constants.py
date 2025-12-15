ACOES_PADRAO = [
    'listar',
    'visualizar',
    'criar',
    'editar',
    'excluir',
    'exportar',
    'imprimir',
]

PERFIS_ESPECIAIS = [
    'superadmin',
]

PERFIS_PADRAO = (
    'superadmin',
    'admin',
    'gerente',
    'vendedores',
    'assistentes',
)

DEFAULT_PERMISSOES_POR_PERFIL = {
    'superadmin': {
        ('perfilweb', 'perfil'): ACOES_PADRAO,
        ('Pedidos', 'pedidovenda'): ACOES_PADRAO,
        ('Produtos', 'produtos'): ACOES_PADRAO,
    },
    'admin': {
        ('perfilweb', 'perfil'): ['listar', 'visualizar', 'editar'],
        ('Pedidos', 'pedidovenda'): ['listar', 'visualizar', 'criar', 'editar', 'imprimir', 'exportar'],
        ('Produtos', 'produtos'): ['listar', 'visualizar', 'exportar'],
    },
    'gerente': {
        ('Pedidos', 'pedidovenda'): ['listar', 'visualizar', 'criar', 'editar', 'imprimir'],
        ('Produtos', 'produtos'): ['listar', 'visualizar'],
    },
    'vendedores': {
        ('Pedidos', 'pedidovenda'): ['listar', 'visualizar', 'criar', 'editar', 'imprimir'],
    },
    'assistentes': {
        ('Pedidos', 'pedidovenda'): ['listar', 'visualizar', 'imprimir'],
        ('Produtos', 'produtos'): ['listar', 'visualizar'],
    },
}
