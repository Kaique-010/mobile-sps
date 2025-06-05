from rest_framework.routers import DefaultRouter
from .views import CaixageralViewSet, MovicaixaViewSet

router = DefaultRouter()
router.register(r'caixageral', CaixageralViewSet, basename='caixageral')
router.register(r'movicaixa', MovicaixaViewSet, basename='movicaixa')

# Endpoints de venda:
# POST /api/movicaixa/iniciar_venda/
# Payload: { "cliente": int, "vendedor": int, "caixa": int }
#
# POST /api/movicaixa/adicionar_item/
# Payload: { "numero_venda": int, "produto": int, "quantidade": decimal, "valor_unitario": decimal }
#
# POST /api/movicaixa/processar_pagamento/
# Payload: { "numero_venda": int, "forma_pagamento": int, "valor": decimal }
# forma_pagamento: 2=Dinheiro, 3=Crédito, 4=Débito, 5=PIX
#
# POST /api/movicaixa/finalizar_venda/
# Payload: { "numero_venda": int }
#
# Consultas úteis:
# GET /api/movicaixa/?movi_nume_vend=123&movi_tipo=1 (itens da venda)
# GET /api/movicaixa/?movi_nume_vend=123&movi_tipo__gt=1 (pagamentos da venda)

urlpatterns = router.urls