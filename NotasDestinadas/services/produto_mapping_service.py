"""
Serviço para mapeamento automático e criação de produtos
a partir de itens de notas destinadas
"""
import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal

logger = logging.getLogger('NotasDestinadas')


class ProdutoMappingService:
    """Serviço para mapear e criar produtos automaticamente"""

    @staticmethod
    def sugerir_produto(
        item: Dict[str, Any],
        empresa: int,
        banco: str = 'default'
    ) -> Optional[str]:
        """
        Sugere um produto cadastrado baseado nos dados do item
        Ordem de prioridade: EAN > Código Fornecedor > Descrição
        """
        from Produtos.models import Produtos
        from django.db.models import Q
        
        try:
            ean = (item.get('ean') or '').strip()
            forn_cod = (item.get('forn_cod') or '').strip()
            descricao = (item.get('descricao') or '').strip()
            
            # 1. Tenta por EAN (mais confiável)
            if ean and ean not in ['SEM GTIN', '']:
                produto = Produtos.objects.using(banco).filter(
                    prod_coba=ean,
                    prod_empr=str(empresa)
                ).first()
                
                if produto:
                    logger.info(f"Produto encontrado por EAN: {produto.prod_codi}")
                    return produto.prod_codi
            
            # 2. Tenta por código do fornecedor
            if forn_cod:
                produto = Produtos.objects.using(banco).filter(
                    prod_codi=forn_cod,
                    prod_empr=str(empresa)
                ).first()
                
                if produto:
                    logger.info(f"Produto encontrado por código: {produto.prod_codi}")
                    return produto.prod_codi
            
            # 3. Tenta por descrição similar (mais arriscado)
            if descricao and len(descricao) > 5:
                # Busca por descrição parcial
                produtos = Produtos.objects.using(banco).filter(
                    prod_nome__icontains=descricao[:20],
                    prod_empr=str(empresa)
                )[:5]
                
                if produtos.count() == 1:
                    produto = produtos.first()
                    logger.info(f"Produto encontrado por descrição: {produto.prod_codi}")
                    return produto.prod_codi
                elif produtos.count() > 1:
                    logger.warning(f"Múltiplos produtos encontrados para '{descricao[:20]}'")
            
            return None
            
        except Exception as e:
            logger.exception(f"Erro ao sugerir produto: {str(e)}")
            return None

    @staticmethod
    def criar_produto_automatico(
        item: Dict[str, Any],
        empresa: int,
        banco: str = 'default',
        usuario_id: int = 0
    ) -> Optional[str]:
        """
        Cria um novo produto automaticamente baseado nos dados do item
        """
        from Produtos.models import Produtos, UnidadeMedida
        
        try:
            forn_cod = (item.get('forn_cod') or '').strip()
            descricao = (item.get('descricao') or '').strip()
            unidade = (item.get('unidade') or 'UN').strip()
            ncm = (item.get('ncm') or '').strip()
            ean = (item.get('ean') or '').strip()
            
            if not forn_cod or not descricao:
                logger.error("Código e descrição são obrigatórios para criar produto")
                return None
            
            # Verifica se já existe
            existe = Produtos.objects.using(banco).filter(
                prod_codi=forn_cod,
                prod_empr=str(empresa)
            ).first()
            
            if existe:
                logger.info(f"Produto {forn_cod} já existe")
                return existe.prod_codi
            
            # Busca unidade de medida
            un_obj = UnidadeMedida.objects.using(banco).filter(
                unid_codi=unidade
            ).first()
            
            if not un_obj:
                # Tenta criar unidade se não existir
                un_obj = UnidadeMedida.objects.using(banco).create(
                    unid_codi=unidade,
                    unid_desc=unidade
                )
                logger.info(f"Unidade {unidade} criada")
            
            # Cria o produto
            produto = Produtos.objects.using(banco).create(
                prod_empr=str(empresa),
                prod_codi=forn_cod,
                prod_nome=descricao[:120],  # Limita tamanho
                prod_unme=un_obj,
                prod_ncm=ncm[:8] if ncm else '',
                prod_coba=ean if ean and ean != 'SEM GTIN' else '',
                prod_ativo=True,
                prod_tipo='P',  # Produto
                prod_orig='0',  # Nacional
            )
            
            logger.info(f"Produto {produto.prod_codi} criado automaticamente")
            return produto.prod_codi
            
        except Exception as e:
            logger.exception(f"Erro ao criar produto: {str(e)}")
            return None

    @staticmethod
    def mapear_itens_nota(
        nota_entrada,
        banco: str = 'default'
    ) -> List[Dict[str, Any]]:
        """
        Mapeia todos os itens de uma nota, sugerindo produtos cadastrados
        """
        from NotasDestinadas.services.entrada_nfe_service import EntradaNFeService
        
        itens = EntradaNFeService.listar_itens(nota_entrada)
        itens_mapeados = []
        
        for item in itens:
            produto_sugerido = ProdutoMappingService.sugerir_produto(
                item=item,
                empresa=nota_entrada.empresa,
                banco=banco
            )
            
            item_mapeado = dict(item)
            item_mapeado['produto_sugerido'] = produto_sugerido
            item_mapeado['mapeado_automaticamente'] = produto_sugerido is not None
            
            itens_mapeados.append(item_mapeado)
        
        return itens_mapeados

    @staticmethod
    def validar_mapeamento(
        entradas: List[Dict[str, Any]],
        empresa: int,
        banco: str = 'default'
    ) -> Dict[str, Any]:
        """
        Valida o mapeamento de produtos antes do processamento
        """
        from Produtos.models import Produtos
        
        resultado = {
            'valido': True,
            'erros': [],
            'avisos': [],
            'produtos_validados': []
        }
        
        for idx, entrada in enumerate(entradas):
            prod_cod = entrada.get('prod')
            
            if not prod_cod:
                resultado['erros'].append({
                    'index': idx,
                    'item': entrada.get('forn_cod'),
                    'erro': 'Produto não informado'
                })
                resultado['valido'] = False
                continue
            
            # Verifica se produto existe
            produto = Produtos.objects.using(banco).filter(
                prod_codi=prod_cod,
                prod_empr=str(empresa)
            ).first()
            
            if not produto:
                resultado['erros'].append({
                    'index': idx,
                    'item': entrada.get('forn_cod'),
                    'erro': f'Produto {prod_cod} não encontrado'
                })
                resultado['valido'] = False
            else:
                # Produto válido
                resultado['produtos_validados'].append({
                    'index': idx,
                    'codigo': prod_cod,
                    'nome': produto.prod_nome,
                    'unidade': produto.prod_unme.unid_codi if produto.prod_unme else None
                })
                
                # Avisos
                if not produto.prod_ativo:
                    resultado['avisos'].append({
                        'index': idx,
                        'produto': prod_cod,
                        'aviso': 'Produto está inativo'
                    })
        
        return resultado

    @staticmethod
    def criar_produtos_faltantes(
        entradas: List[Dict[str, Any]],
        empresa: int,
        banco: str = 'default',
        usuario_id: int = 0
    ) -> Dict[str, Any]:
        """
        Cria automaticamente produtos que não foram mapeados
        """
        resultado = {
            'produtos_criados': [],
            'produtos_existentes': [],
            'erros': []
        }
        
        for idx, entrada in enumerate(entradas):
            prod_cod = entrada.get('prod')
            
            # Se já tem produto mapeado, pula
            if prod_cod:
                resultado['produtos_existentes'].append(prod_cod)
                continue
            
            # Tenta criar produto automaticamente
            try:
                novo_cod = ProdutoMappingService.criar_produto_automatico(
                    item=entrada,
                    empresa=empresa,
                    banco=banco,
                    usuario_id=usuario_id
                )
                
                if novo_cod:
                    resultado['produtos_criados'].append({
                        'index': idx,
                        'codigo': novo_cod,
                        'forn_cod': entrada.get('forn_cod'),
                        'descricao': entrada.get('descricao')
                    })
                    
                    # Atualiza entrada com novo código
                    entrada['prod'] = novo_cod
                else:
                    resultado['erros'].append({
                        'index': idx,
                        'forn_cod': entrada.get('forn_cod'),
                        'erro': 'Não foi possível criar produto'
                    })
                    
            except Exception as e:
                resultado['erros'].append({
                    'index': idx,
                    'forn_cod': entrada.get('forn_cod'),
                    'erro': str(e)
                })
        
        return resultado

    @staticmethod
    def buscar_produtos_similar(
        query: str,
        empresa: int,
        banco: str = 'default',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca produtos similares para auxiliar no mapeamento manual
        """
        from Produtos.models import Produtos
        from django.db.models import Q
        
        if not query or len(query) < 2:
            return []
        
        try:
            produtos = Produtos.objects.using(banco).filter(
                Q(prod_codi__icontains=query) |
                Q(prod_nome__icontains=query) |
                Q(prod_coba__icontains=query),
                prod_empr=str(empresa)
            )[:limit]
            
            return [{
                'codigo': p.prod_codi,
                'nome': p.prod_nome,
                'ean': p.prod_coba,
                'unidade': p.prod_unme.unid_codi if p.prod_unme else None,
                'ativo': p.prod_ativo
            } for p in produtos]
            
        except Exception as e:
            logger.exception(f"Erro ao buscar produtos: {str(e)}")
            return []