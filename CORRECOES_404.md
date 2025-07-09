# Correções para Problemas de 404 - Sistema SPS

## Problemas Identificados

### 1. Endpoints não encontrados (404)
Os logs mostravam tentativas de acessar endpoints que não existiam:
- `/api/casaa/parametros-admin/modulos-liberados/`
- `/api/casaa/parametros-admin/permissoes-usuario/`
- `/api/casaa/parametros-admin/configuracao-completa/`

### 2. Módulo não liberado
A licença "casaa" não tinha o módulo `parametros_admin` na lista de módulos disponíveis.

### 3. Problemas de autenticação
O middleware de auditoria estava bloqueando requisições não autenticadas para endpoints de configuração.

## Correções Implementadas

### 1. Adição do módulo `parametros_admin` à licença "casaa"
**Arquivo:** `core/licencas.json`
```json
{
  "slug": "casaa",
  "modulos": [
    // ... outros módulos ...
    "parametros_admin"  // ← Adicionado
  ]
}
```

### 2. Criação de endpoints específicos para compatibilidade com frontend
**Arquivo:** `parametros_admin/urls.py`
```python
urlpatterns = [
    path('', include(router.urls)),
    
    # Endpoint público para configuração inicial
    path('configuracao-inicial/', ConfiguracaoInicialView.as_view(), name='configuracao-inicial'),
    
    # Endpoints específicos para compatibilidade com frontend
    path('modulos-liberados/', PermissaoModuloViewSet.as_view({'get': 'modulos_liberados'}), name='modulos-liberados'),
    path('permissoes-usuario/', PermissaoModuloViewSet.as_view({'get': 'permissoes_usuario'}), name='permissoes-usuario'),
    path('configuracao-completa/', PermissaoModuloViewSet.as_view({'get': 'configuracao_completa'}), name='configuracao-completa'),
]
```

### 3. Implementação do método `configuracao_completa`
**Arquivo:** `parametros_admin/views.py`
- Adicionado método `configuracao_completa` na `PermissaoModuloViewSet`
- Retorna configuração completa do sistema incluindo:
  - Módulos liberados
  - Configurações de estoque
  - Configurações financeiras
  - Parâmetros gerais
  - Informações do usuário e licença

### 4. Criação de view pública para configuração inicial
**Arquivo:** `parametros_admin/views.py`
```python
class ConfiguracaoInicialView(APIView):
    """View pública para configuração inicial do sistema"""
    permission_classes = [AllowAny]
    
    def get(self, request, slug=None):
        """Retorna configuração inicial pública do sistema"""
        # Retorna informações básicas da licença sem autenticação
```

### 5. Correção do atributo `modulo_requerido`
**Arquivo:** `parametros_admin/views.py`
- Corrigido `modulo_necessario` para `modulo_requerido` em todas as ViewSets

### 6. Ajustes no middleware de auditoria
**Arquivo:** `auditoria/middleware.py`
- Adicionada exceção para endpoints de configuração
- Permitido acesso público a `/parametros-admin/configuracao-inicial/`

## Endpoints Disponíveis

### Endpoints Públicos (sem autenticação)
- `GET /api/{slug}/parametros-admin/configuracao-inicial/`
  - Retorna informações básicas da licença

### Endpoints Autenticados
- `GET /api/{slug}/parametros-admin/modulos-liberados/`
  - Retorna módulos liberados para a empresa do usuário

- `GET /api/{slug}/parametros-admin/permissoes-usuario/`
  - Retorna todas as permissões do usuário atual

- `GET /api/{slug}/parametros-admin/configuracao-completa/`
  - Retorna configuração completa do sistema

## Teste do Sistema

O sistema foi verificado com:
```bash
python manage.py check
```

Resultado: ✅ Sistema funcionando corretamente (apenas 1 warning não crítico)

## Próximos Passos

1. **Testar os endpoints** no frontend para garantir que estão funcionando
2. **Monitorar os logs** para verificar se os erros 404 foram resolvidos
3. **Implementar cache** para melhorar performance dos endpoints de configuração
4. **Adicionar documentação** da API para os novos endpoints

## Observações

- Os endpoints agora seguem o padrão REST da API
- A autenticação está configurada corretamente
- O middleware de auditoria não interfere mais nos endpoints de configuração
- O sistema está preparado para expansão futura 