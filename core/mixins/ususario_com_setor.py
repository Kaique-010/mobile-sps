from Licencas.models import Usuarios
from core.utils import get_licenca_db_config
from core.middleware import get_licenca_slug



from core.licenca_context import get_licencas_map

class UsuarioComSetorMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        slug = get_licenca_slug()
        db_alias = get_licenca_db_config(request)
        licencas = get_licencas_map()
        licenca_info = next((l for l in licencas if l.get('slug') == slug), None)
        
        db_name = licenca_info.get('db_name', '') if licenca_info else ''
        is_banco_144 = '144' in db_name
        usuario = request.user
        tem_setor = False
        setor_id = None
        if usuario and usuario.is_authenticated:
            # Verifica se usua_seto não é nulo
            setor_id = getattr(usuario, "usua_seto", None) or getattr(usuario, "setor", None)
            print(f"setor_id: {setor_id}")
            
            # Se não encontrou no usuário, tenta pegar do token (payload)
            if not setor_id and hasattr(request, 'auth') and request.auth:
                try:
                    # Suporte para dict ou objeto com get (SimpleJWT AccessToken)
                    if hasattr(request.auth, 'get'):
                        setor_id = request.auth.get('setor')
                    elif isinstance(request.auth, dict):
                         setor_id = request.auth.get('setor')
                    # Fallback para atributo payload
                    elif hasattr(request.auth, 'payload') and isinstance(request.auth.payload, dict):
                        setor_id = request.auth.payload.get('setor')
                except Exception:
                    pass
            
            if setor_id:
                try:
                    setor_id = int(setor_id)
                    tem_setor = True
                except (ValueError, TypeError):
                    setor_id = None
                    tem_setor = False

        request.licenca_ctx = {
            'slug': slug,
            'banco': db_alias,
            'tem_setor': tem_setor,
            'setor_id': setor_id,
            'is_banco_144': is_banco_144,
        }