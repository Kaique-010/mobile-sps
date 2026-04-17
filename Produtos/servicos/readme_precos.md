# preços promocionais 

<br />

echado — já está integrado no Caixa , Pedidos e Orçamentos com switch + modal (seleção À vista / A prazo) e endpoints retornando as opções.

Caixa (Web)

- Switch “Usar preços promocionais” + modal de escolha À vista/A prazo em aba\_produtos.html .
- Ao selecionar produto:
  - se switch ligado: chama /web/{slug}/pedidos/preco/?prod\_codi=...\&pedi\_fina=0\&promocional=1\&opcoes=1 e abre modal com os 2 preços.
- Ao adicionar/atualizar item, envia preco\_origem e preco\_tipo e o backend respeita isso (busca na tabela normal ou promocional e grava o unitário correto):
  - venda\_adicionar\_item
  - venda\_atualizar\_item
    Pedidos (Web)
- Switch + modal em pedidocriar.html .
- No autocomplete do produto, se o switch estiver ligado, busca promocional=1\&opcoes=1 e abre modal para escolher À vista/A prazo antes de preencher o unitário.
  Orçamentos (Web)
- Switch + modal em orcamentocriar.html .
- Mesmo comportamento: se switch ligado, abre modal com preços promocionais e aplica no iped\_unit .
  Endpoints (Web) ajustados
- Pedidos: preco\_produto agora aceita:
  - promocional=1 (tenta usar promocional)
  - opcoes=1 (retorna prices.normal e prices.promocional com avista/prazo )
  - modo=avista|prazo (opcional; default segue pedi\_fina )
- Orçamentos: preco\_produto com os mesmos parâmetros.
  Endpoints (REST) para consumo via app/mobile
- Pedidos REST: GET /.../pedidos/preco-produto/?prod\_codi=...\&promocional=1\&opcoes=1 em PedidoVendaViewSet.preco\_produto
- Caixa REST: GET /.../caixa/preco\_produto/?prod\_codi=...\&promocional=1\&opcoes=1 em CaixaViewSet.preco\_produto
  Se você me disser o padrão exato das rotas REST (prefixo/namespace do router do Caixa e do Pedidos no seu projeto), eu te devolvo os exemplos de URL completos já no formato final do seu ambiente.

