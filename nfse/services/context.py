

class NfseContext:
        def __init__(self, *, db_alias, empresa_id, filial_id, slug, user=None):
            self.db_alias = db_alias
            self.empresa_id = int(empresa_id) if empresa_id else None
            self.filial_id = int(filial_id) if filial_id else None
            self.slug = slug
            self.user = user

        @classmethod
        def from_request(cls, request, slug):
            return cls(
                db_alias=getattr(request, 'db_alias', None),
                empresa_id=getattr(request, 'empresa_id', None) or request.session.get('empresa_id'),
                filial_id=getattr(request, 'filial_id', None) or request.session.get('filial_id'),
                slug=slug,
                user=getattr(request, 'user', None),
            )