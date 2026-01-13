from django.test import TestCase
from decimal import Decimal
from Notas_Fiscais.emissao.gerador_xml import GeradorXML

class XmlGenerationTest(TestCase):
    def test_gerar_e_imprimir_xml(self):
        print("\n\n=== INÍCIO GERAÇÃO XML ===")
        
        # DTO completo simulando uma nota já calculada
        dto = {
            "chave": "35231012345678000199550010000001001000000015",
            "cNF": "00000001",
            "natOp": "VENDA DE MERCADORIA",
            "modelo": "55",
            "serie": "1",
            "numero": 100,
            "data_emissao": "2023-10-27T10:00:00-03:00",
            "tipo_operacao": 1, # Saída
            "finalidade": 1,    # Normal
            "ambiente": 2,      # Homologação
            
            "emitente": {
                "cnpj": "12345678000199",
                "razao": "EMPRESA EMITENTE LTDA",
                "ie": "123456789",
                "uf": "SP",
                "cUF": "35",
                "logradouro": "RUA DO EMITENTE",
                "numero": "1000",
                "bairro": "CENTRO",
                "municipio": "SAO PAULO",
                "cod_municipio": "3550308",
                "cep": "01001000"
            },
            
            "destinatario": {
                "documento": "98765432000198",
                "nome": "CLIENTE DESTINATARIO SA",
                "uf": "SP",
                "logradouro": "AVENIDA DO CLIENTE",
                "numero": "500",
                "bairro": "JARDINS",
                "municipio": "SAO PAULO",
                "cod_municipio": "3550308",
                "cep": "01002000"
            },
            
            "itens": [
                {
                    "codigo": "PROD001",
                    "descricao": "PRODUTO TESTE A",
                    "ncm": "10203040",
                    "cfop": "5102",
                    "unidade": "UN",
                    "quantidade": 10.0,
                    "valor_unit": 100.00,
                    "desconto": 0.0,
                    
                    # Frete/Seguro/Outras
                    "valor_frete": 50.00,
                    "valor_seguro": 10.00,
                    "valor_outras_despesas": 5.00,
                    
                    # ICMS Normal (CST 00)
                    "cst_icms": "00",
                    "base_icms": 1000.00,
                    "aliq_icms": 18.00,
                    "valor_icms": 180.00,
                    
                    # PIS (CST 01)
                    "cst_pis": "01",
                    "base_pis": 1000.00,
                    "aliq_pis": 1.65,
                    "valor_pis": 16.50,
                    
                    # COFINS (CST 01)
                    "cst_cofins": "01",
                    "base_cofins": 1000.00,
                    "aliq_cofins": 7.60,
                    "valor_cofins": 76.00,
                    
                    # IBS/CBS (Reforma Tributária)
                    "cst_ibs": "01",
                    "base_ibs": 1000.00,
                    "aliq_ibs": 17.00,
                    "valor_ibs": 170.00,
                    
                    "cst_cbs": "01",
                    "base_cbs": 1000.00,
                    "aliq_cbs": 9.00,
                    "valor_cbs": 90.00,
                    
                    # Campos opcionais zerados/None
                    "valor_ipi": 0.0,
                    "valor_icms_st": 0.0,
                    "base_icms_st": 0.0,
                    "valor_fcp": 0.0
                }
            ],
            
            "tpag": "01" # Dinheiro
        }
        
        gerador = GeradorXML()
        xml = gerador.gerar(dto)
        
        # Pretty print manual para facilitar leitura no output
        from lxml import etree
        root = etree.fromstring(xml.encode('utf-8'))
        xml_pretty = etree.tostring(root, pretty_print=True, encoding="unicode")
        
        print(xml_pretty)
        print("=== FIM GERAÇÃO XML ===\n")
