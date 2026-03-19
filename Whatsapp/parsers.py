class WhatsAppOrderParser:

    def parse(self, message):
        order = message.get("order", {})
        itens = []

        for item in order.get("product_items", []):
            itens.append({
                "codigo": item["product_retailer_id"],  # 🔑 vem do ERP
                "quantidade": item["quantity"]
            })

        return itens