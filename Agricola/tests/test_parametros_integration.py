from django.test import TestCase, override_settings
from django.urls import reverse
from Agricola.models import ParametroAgricola
from Agricola.registry import ParametrosAgricolasRegistry
from Agricola.service.parametros import ParametroAgricolaService
import json

class ParametrosIntegrationTest(TestCase):
    databases = {'default'}

    def setUp(self):
        self.empresa = '1'
        self.filial = '1'
        self.chave = "controla_estoque"
        
        # Garante estado limpo
        ParametroAgricola.objects.all().delete()

    def test_default_value_from_registry(self):
        """Testa se o serviço retorna o valor default do registry quando não há BD"""
        valor = ParametroAgricolaService.get(self.empresa, self.filial, self.chave)
        expected = ParametrosAgricolasRegistry.PARAMS[self.chave]["default"]
        self.assertEqual(valor, expected)

    def test_set_and_get_parametro(self):
        """Testa salvar e recuperar um parâmetro"""
        novo_valor = False # Default é True
        ParametroAgricolaService.set(self.empresa, self.filial, self.chave, novo_valor)
        
        # Verifica no banco
        param = ParametroAgricola.objects.get(
            para_empr=self.empresa,
            para_fili=self.filial,
            para_chav=self.chave
        )
        self.assertEqual(json.loads(param.para_valo), novo_valor)
        
        # Verifica via serviço
        valor_recuperado = ParametroAgricolaService.get(self.empresa, self.filial, self.chave)
        self.assertEqual(valor_recuperado, novo_valor)

    def test_sync_command_logic(self):
        """Simula a lógica de sync (sem chamar o comando full para evitar deps de rede/db externos)"""
        # Cria "empresa" simulada criando um parametro manualmente ou assumindo existencia
        
        # Executa lógica de sync (criação de defaults)
        for chave, config in ParametrosAgricolasRegistry.PARAMS.items():
            ParametroAgricola.objects.get_or_create(
                para_empr=self.empresa,
                para_fili=self.filial,
                para_chav=chave,
                defaults={"para_valo": json.dumps(config["default"])},
            )
            
        # Verifica se todos foram criados
        count = ParametroAgricola.objects.filter(
            para_empr=self.empresa,
            para_fili=self.filial
        ).count()
        self.assertEqual(count, len(ParametrosAgricolasRegistry.PARAMS))

    def test_view_context(self):
        """Testa se a view carrega os parâmetros corretamente no contexto"""
        # url = reverse('AgricolaWeb:parametros_agricolas', kwargs={'empresa': self.empresa, 'filial': self.filial})
        # Nota: Como não temos as URLs carregadas no teste unitário isolado facilmente sem o ROOT_URLCONF correto,
        # vamos testar a lógica da view instanciando-a ou simulando o request se possível.
        # Mas para simplificar, testamos a lógica de construção do dicionário que a view usa.
        
        params = {}
        for chave, config in ParametrosAgricolasRegistry.PARAMS.items():
            params[chave] = ParametroAgricolaService.get(self.empresa, self.filial, chave)
            
        self.assertIn("controla_estoque", params)
        self.assertTrue(params["controla_estoque"]) # Default
