class CriarPedidoViaWhatsApp:
    def executar(self, dados):
        cliente = dados.get("cliente")
        itens = dados.get("itens")
        # 📞 cria pedido no ERP
        CriarPedido().executar({
            "cliente": cliente,
            "itens": itens
        })
    def envia_confirmacao(self, cliente):
        EnviarMensagemWhatsApp().executar({
            "numero": cliente,
            "mensagem": "Seu pedido foi criado com sucesso!"
        })
