# App TrocasDevolucoes

App para gestão de trocas e devoluções em arquitetura horizontal, com:

- Camada REST (`rest/`)
- Camada WEB (`Web/`)
- Camada de serviços (`services/`)

Padrões aplicados:

- Views magras, com lógica central em service.
- Campos do model no padrão de prefixo + 4 letras (`tdvl_*`, `itdv_*`).
- Estrutura espelhada no app de Pedidos.
