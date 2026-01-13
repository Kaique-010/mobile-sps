from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import TestCase
from Notas_Fiscais.emissao.emissao_nota_service import EmissaoNotaService
from Notas_Fiscais.emissao.exceptions import ErroValidacao
from Notas_Fiscais.models import Nota, NotaItem, NotaItemImposto
from Licencas.models import Filiais
from Entidades.models import Entidades
from Produtos.models import Produtos, UnidadeMedida

class EmissionFlowTest(TestCase):
    def setUp(self):
        # Create dependencies
        self.empresa = 1
        self.filial_id = 1
        
        self.unidade = UnidadeMedida.objects.create(
            unid_codi="UN",
            unid_desc="Unidade"
        )
        print(f"DEBUG: self.unidade type: {type(self.unidade)}")
        print(f"DEBUG: self.unidade: {self.unidade}")
        
        self.filial_obj = Filiais.objects.create(
            empr_empr=self.empresa,
            empr_codi=self.filial_id,
            empr_docu="12345678000199",
            empr_nome="Minha Empresa",
            empr_regi_trib="3",
            empr_ende="Rua Teste",
            empr_nume="100",
            empr_bair="Centro",
            empr_cida="Cidade",
            empr_esta="SP",
            empr_cep="12345000",
            empr_cert_digi=b"fake_cert"
        )

        self.cliente = Entidades.objects.create(
            enti_empr=self.empresa,
            enti_clie=100,
            enti_nome="Cliente Teste",
            enti_cnpj="98765432000198",
            enti_ende="Rua Cliente",
            enti_nume="200",
            enti_cida="Cidade",
            enti_esta="SP",
            enti_cep="12345000"
        )

        self.produto = Produtos.objects.create(
            prod_codi="1",
            prod_nome="Produto Teste",
            prod_ncm="12345678",
            prod_empr=self.empresa,
            prod_unme=self.unidade
        )

        self.dto = {
            "numero": 100,
            "serie": "1",
            "tipo_operacao": 1,
            "finalidade": 1,
            "ambiente": 2,
            "emitente": {
                "cnpj": self.filial_obj.empr_docu,
                "razao": self.filial_obj.empr_nome,
                "uf": self.filial_obj.empr_esta,
                "logradouro": self.filial_obj.empr_ende,
                "numero": self.filial_obj.empr_nume,
                "municipio": self.filial_obj.empr_cida,
                "cod_municipio": "3550308",
                "cep": self.filial_obj.empr_cep,
                "ie": "123"
            },
            "destinatario": {
                "documento": self.cliente.enti_cnpj,
                "nome": self.cliente.enti_nome,
                "uf": self.cliente.enti_esta,
                "logradouro": self.cliente.enti_ende,
                "numero": self.cliente.enti_nume,
                "municipio": self.cliente.enti_cida,
                "cod_municipio": "3550308",
                "cep": self.cliente.enti_cep,
                "bairro": "Centro"
            },
            "itens": [
                {
                    "codigo": self.produto.prod_codi,
                    "descricao": self.produto.prod_nome,
                    "quantidade": 10,
                    "valor_unit": 100,
                    "ncm": "12345678",
                    "cfop": "5102",
                    "cst_icms": "00",
                    "cst_pis": "01",
                    "cst_cofins": "01",
                    "valor_frete": 50.00,
                    "valor_seguro": 10.00,
                    "valor_outras_despesas": 5.00
                }
            ]
        }

    @patch("Notas_Fiscais.emissao.emissao_nota_service.EmissaoServiceCore")
    @patch("Notas_Fiscais.emissao.emissao_nota_service.CalculoImpostosService")
    def test_emitir_nota_success(self, MockCalculo, MockEmissorCore):
        # Setup mocks
        mock_emissor = MockEmissorCore.return_value
        mock_emissor.emitir.return_value = ({"status": "100", "chave": "123"}, "<xml>...</xml>", "<retorno>...</retorno>")
        
        # Mock calculation to set taxes on item
        def side_effect_calc(nota):
            item = nota.itens.first()
            # Simulate Tax Calculation
            NotaItemImposto.objects.create(
                item=item,
                icms_base=1000, icms_aliquota=18, icms_valor=180,
                pis_base=1000, pis_aliquota=1.65, pis_valor=16.50,
                cofins_base=1000, cofins_aliquota=7.60, cofins_valor=76.00,
                # Simulate ST if needed, but CST is 00 here
            )
            item.cst_icms = "00"
            item.cst_pis = "01"
            item.cst_cofins = "01"
            item.save()

        MockCalculo.return_value.aplicar_impostos.side_effect = side_effect_calc

        result = EmissaoNotaService.emitir_nota(self.dto, self.empresa, self.filial_id)
        
        self.assertEqual(result["sefaz"]["status"], "100")
        
        # Verify validations
        nota = result["nota"]
        self.assertEqual(nota.status, 100) # Autorizada
        
        # Verify XML generation call (indirectly via mock args if we want, but logic is inside)
        args, _ = MockEmissorCore.call_args
        dto_generated = args[0]
        item_dto = dto_generated["itens"][0]
        
        self.assertEqual(item_dto["valor_frete"], Decimal("50.00"))
        self.assertEqual(item_dto["valor_seguro"], Decimal("10.00"))
        self.assertEqual(item_dto["valor_outras_despesas"], Decimal("5.00"))

    def test_validacao_inicial_falha(self):
        dto_invalido = self.dto.copy()
        dto_invalido.pop("destinatario")
        
        with self.assertRaises(ErroValidacao):
            EmissaoNotaService.emitir_nota(dto_invalido, self.empresa, self.filial_id)

    @patch("Notas_Fiscais.emissao.emissao_nota_service.CalculoImpostosService")
    def test_validacao_calculada_falha(self, MockCalculo):
        # Simulate calculation failure (no taxes created)
        MockCalculo.return_value.aplicar_impostos.return_value = None
        
        with self.assertRaises(ErroValidacao) as cm:
            EmissaoNotaService.emitir_nota(self.dto, self.empresa, self.filial_id)
        
        self.assertIn("Impostos não foram calculados", str(cm.exception))

    @patch("Notas_Fiscais.emissao.emissao_nota_service.EmissaoServiceCore")
    @patch("Notas_Fiscais.emissao.emissao_nota_service.CalculoImpostosService")
    def test_emitir_nota_com_st(self, MockCalculo, MockEmissorCore):
        # Update DTO for ST
        self.dto["itens"][0]["cst_icms"] = "10"
        
        mock_emissor = MockEmissorCore.return_value
        mock_emissor.emitir.return_value = ({"status": "100", "chave": "123"}, "<xml>...</xml>", "<retorno>...</retorno>")
        
        def side_effect_calc(nota):
            item = nota.itens.first()
            NotaItemImposto.objects.create(
                item=item,
                icms_base=1000, icms_aliquota=18, icms_valor=180,
                icms_st_base=1500, icms_st_aliquota=18, icms_mva_st=50,
                # ST Net = 270 - 180 = 90 (simplified logic, usually stored as final value)
                # But here we store whatever the calculator gives.
                icms_st_valor=90, 
                pis_base=1000, pis_aliquota=1.65, pis_valor=16.50,
                cofins_base=1000, cofins_aliquota=7.60, cofins_valor=76.00
            )
            item.cst_icms = "10"
            item.cst_pis = "01"
            item.cst_cofins = "01"
            item.save()

        MockCalculo.return_value.aplicar_impostos.side_effect = side_effect_calc

        result = EmissaoNotaService.emitir_nota(self.dto, self.empresa, self.filial_id)
        
        args, _ = MockEmissorCore.call_args
        dto_generated = args[0]
        item_dto = dto_generated["itens"][0]
        
        self.assertEqual(item_dto["valor_icms_st"], Decimal("90"))
        self.assertEqual(item_dto["mva_st"], Decimal("50"))
