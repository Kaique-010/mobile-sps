from django.views import View
from django.shortcuts import render, redirect
from .registry import ParametrosAgricolasRegistry
from core.utils import get_licenca_db_config
from .service.parametros import ParametroAgricolaService


class ParametrosAgricolasView(View):
    def get_context_info(self, request):
        empresa = getattr(request.user, 'empresa', None) or request.session.get('empresa_id', 1)
        filial = getattr(request.user, 'filial', None) or request.session.get('filial_id', 1)
        # Se vierem como objeto (do request.user), converte para ID
        if hasattr(empresa, 'id'): empresa = empresa.id
        if hasattr(filial, 'id'): filial = filial.id
        return int(empresa), int(filial)

    def post(self, request, *args, **kwargs):
        empresa, filial = self.get_context_info(request)
        banco = get_licenca_db_config(request) or 'default'
        parametros = []
        for chave, config in ParametrosAgricolasRegistry.PARAMS.items():
            valor = request.POST.get(chave, config["default"])
            if config["tipo"] == bool:
                valor = valor == "True"
            ParametroAgricolaService.set(empresa, filial, chave, valor, using=banco)
            parametros.append({
                "chave": chave,
                "valor": valor,
            })
        return self.get(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        empresa, filial = self.get_context_info(request)
        banco = get_licenca_db_config(request) or 'default'
        
        print(f"[DEBUG] ParametrosAgricolasView.get - Empresa: {empresa} | Filial: {filial} | Banco: {banco}")

        parametros_list = []
        for chave, config in ParametrosAgricolasRegistry.PARAMS.items():
            valor_atual = ParametroAgricolaService.get(empresa, filial, chave, using=banco)
            
            # Monta objeto completo para o template
            param_obj = {
                "chave": chave,
                "valor": valor_atual,
                "label": config.get("label", chave),
                "grupo": config.get("grupo", "Geral"),
                "tipo": config.get("tipo", str),
                "is_bool": config.get("tipo") == bool,
                "default": config.get("default"),
            }
            parametros_list.append(param_obj)
            print(f"[DEBUG] Carregado param: {chave} = {valor_atual} (Grupo: {param_obj['grupo']})")

        # Ordena por grupo para o regroup funcionar corretamente
        parametros_list.sort(key=lambda x: x['grupo'])
        
        return render(request, "agricola/parametros_agricolas.html", {"parametros": parametros_list})
