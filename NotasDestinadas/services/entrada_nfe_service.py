"""
Serviço para processamento de entradas de NF-e
Lida com mapeamento de produtos, geração de estoque e contas a pagar
"""
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from django.core.exceptions import ValidationError
from django.db import transaction
import re

logger = logging.getLogger('NotasDestinadas')


class EntradaNFeService:
    """Serviço para processamento de entrada de NF-e"""

    @staticmethod
    def registrar_entrada(
        xml: str,
        empresa: int,
        filial: int,
        cliente: Optional[int] = None,
        gerar_estoque: bool = True,
        gerar_contas_pagar: bool = True,
        banco: str = 'default',
        usuario_id: int = 0
    ):
        """
        Registra uma nota fiscal de entrada a partir do XML
        """
        from NotasDestinadas.models import NotaFiscalEntrada
        
        try:
            # Parse do XML
            root = ET.fromstring(xml)
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Extrai dados da nota
            ide = root.find('.//nfe:ide', ns)
            emit = root.find('.//nfe:emit', ns)
            dest = root.find('.//nfe:dest', ns)
            total = root.find('.//nfe:total/nfe:ICMSTot', ns)
            
            if not all([ide, emit, dest, total]):
                logger.error("XML incompleto - faltam tags obrigatórias")
                raise ValueError("XML da NF-e está incompleto")
            
            # Monta dados da nota
            dados_nota = {
                'empresa': empresa,
                'filial': filial,
                'cliente': cliente,
                'xml_nfe': xml,
                
                # Identificação
                'codigo_uf_emitente': EntradaNFeService._get_text(ide, 'nfe:cUF', ns, int),
                'codigo_numerico_chave': EntradaNFeService._get_text(ide, 'nfe:cNF', ns, int),
                'natureza_operacao': EntradaNFeService._get_text(ide, 'nfe:natOp', ns),
                'modelo': EntradaNFeService._get_text(ide, 'nfe:mod', ns),
                'serie': EntradaNFeService._get_text(ide, 'nfe:serie', ns),
                'numero_nota_fiscal': EntradaNFeService._get_text(ide, 'nfe:nNF', ns, int),
                'data_emissao': EntradaNFeService._get_text(ide, 'nfe:dhEmi', ns, EntradaNFeService._parse_date),
                'tipo_operacao': EntradaNFeService._get_text(ide, 'nfe:tpNF', ns, int),
                
                # Emitente
                'emitente_cnpj': EntradaNFeService._get_text(emit, 'nfe:CNPJ', ns),
                'emitente_cpf': EntradaNFeService._get_text(emit, 'nfe:CPF', ns),
                'emitente_razao_social': EntradaNFeService._get_text(emit, 'nfe:xNome', ns),
                'emitente_nome_fantasia': EntradaNFeService._get_text(emit, 'nfe:xFant', ns),
                'emitente_ie': EntradaNFeService._get_text(emit, 'nfe:IE', ns),
                
                # Endereço emitente
                'emitente_logradouro': EntradaNFeService._get_text(emit, './/nfe:xLgr', ns),
                'emitente_numero': EntradaNFeService._get_text(emit, './/nfe:nro', ns),
                'emitente_complemento': EntradaNFeService._get_text(emit, './/nfe:xCpl', ns),
                'emitente_bairro': EntradaNFeService._get_text(emit, './/nfe:xBairro', ns),
                'emitente_codigo_municipio': EntradaNFeService._get_text(emit, './/nfe:cMun', ns, int),
                'emitente_nome_municipio': EntradaNFeService._get_text(emit, './/nfe:xMun', ns),
                'emitente_uf': EntradaNFeService._get_text(emit, './/nfe:UF', ns),
                'emitente_cep': EntradaNFeService._get_text(emit, './/nfe:CEP', ns, int),
                'emitente_fone': EntradaNFeService._get_text(emit, './/nfe:fone', ns),
                
                # Destinatário
                'destinatario_cnpj': EntradaNFeService._get_text(dest, 'nfe:CNPJ', ns),
                'destinatario_cpf': EntradaNFeService._get_text(dest, 'nfe:CPF', ns),
                'destinatario_razao_social': EntradaNFeService._get_text(dest, 'nfe:xNome', ns),
                'destinatario_ie': EntradaNFeService._get_text(dest, 'nfe:IE', ns),
                'destinatario_email': EntradaNFeService._get_text(dest, 'nfe:email', ns),
                
                # Endereço destinatário
                'destinatario_logradouro': EntradaNFeService._get_text(dest, './/nfe:xLgr', ns),
                'destinatario_numero': EntradaNFeService._get_text(dest, './/nfe:nro', ns),
                'destinatario_complemento': EntradaNFeService._get_text(dest, './/nfe:xCpl', ns),
                'destinatario_bairro': EntradaNFeService._get_text(dest, './/nfe:xBairro', ns),
                'destinatario_codigo_municipio': EntradaNFeService._get_text(dest, './/nfe:cMun', ns, int),
                'destinatario_nome_municipio': EntradaNFeService._get_text(dest, './/nfe:xMun', ns),
                'destinatario_uf': EntradaNFeService._get_text(dest, './/nfe:UF', ns),
                'destinatario_cep': EntradaNFeService._get_text(dest, './/nfe:CEP', ns, int),
                'destinatario_fone': EntradaNFeService._get_text(dest, './/nfe:fone', ns),
                
                # Totais
                'valor_total_produtos': EntradaNFeService._get_text(total, 'nfe:vProd', ns, Decimal),
                'valor_total_nota': EntradaNFeService._get_text(total, 'nfe:vNF', ns, Decimal),
                'valor_total_desconto': EntradaNFeService._get_text(total, 'nfe:vDesc', ns, Decimal),
                'valor_total_frete': EntradaNFeService._get_text(total, 'nfe:vFrete', ns, Decimal),
                'valor_total_seguro': EntradaNFeService._get_text(total, 'nfe:vSeg', ns, Decimal),
                'valor_total_icms': EntradaNFeService._get_text(total, 'nfe:vICMS', ns, Decimal),
                'valor_total_ipi': EntradaNFeService._get_text(total, 'nfe:vIPI', ns, Decimal),
                'valor_total_pis': EntradaNFeService._get_text(total, 'nfe:vPIS', ns, Decimal),
                'valor_total_cofins': EntradaNFeService._get_text(total, 'nfe:vCOFINS', ns, Decimal),
                'valor_total_outras_despesas': EntradaNFeService._get_text(total, 'nfe:vOutro', ns, Decimal),
                
                # Status
                'status_nfe': 100,  # Autorizada
                'cancelada': False,
                'inutilizada': False,
                'denegada': False,
            }
            
            # Protocolo se existir
            prot_nfe = root.find('.//nfe:protNFe', ns)
            if prot_nfe:
                dados_nota['protocolo_nfe'] = EntradaNFeService._get_text(prot_nfe, 'nfe:nProt', ns)
            
            # Cria ou atualiza a nota
            nota, created = NotaFiscalEntrada.objects.using(banco).update_or_create(
                empresa=empresa,
                filial=filial,
                numero_nota_fiscal=dados_nota['numero_nota_fiscal'],
                serie=dados_nota['serie'],
                defaults=dados_nota
            )
            
            logger.info(f"Nota {nota.numero_nota_fiscal} {'criada' if created else 'atualizada'}")
            
            return nota
            
        except Exception as e:
            logger.exception(f"Erro ao registrar entrada: {str(e)}")
            raise

    @staticmethod
    def listar_itens(nota_entrada) -> List[Dict[str, Any]]:
        """
        Extrai itens do XML da nota para preprocessamento
        """
        itens = []
        
        try:
            if not nota_entrada.xml_nfe:
                return itens
            
            root = ET.fromstring(nota_entrada.xml_nfe)
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                if prod is None:
                    continue
                
                item = {
                    'nItem': det.get('nItem', ''),
                    'forn_cod': (prod.findtext('nfe:cProd', '', ns) or '').strip(),
                    'descricao': (prod.findtext('nfe:xProd', '', ns) or '').strip(),
                    'ncm': (prod.findtext('nfe:NCM', '', ns) or '').strip(),
                    'cfop': (prod.findtext('nfe:CFOP', '', ns) or '').strip(),
                    'unidade': (prod.findtext('nfe:uCom', '', ns) or '').strip(),
                    'ean': (prod.findtext('nfe:cEAN', '', ns) or '').strip(),
                }
                
                # Valores numéricos
                try:
                    item['quantidade'] = float(prod.findtext('nfe:qCom', '0', ns) or 0)
                except:
                    item['quantidade'] = None
                
                try:
                    item['valor_unit'] = float(prod.findtext('nfe:vUnCom', '0', ns) or 0)
                except:
                    item['valor_unit'] = None
                
                try:
                    item['valor_total'] = float(prod.findtext('nfe:vProd', '0', ns) or 0)
                except:
                    item['valor_total'] = None
                
                itens.append(item)
            
        except Exception as e:
            logger.exception(f"Erro ao listar itens: {str(e)}")
        
        return itens

    @staticmethod
    def confirmar_processamento(
        nota_entrada,
        entradas: List[Dict[str, Any]],
        banco: str = 'default',
        usuario_id: int = 0,
        duplicatas_override: Optional[List[Dict[str, Any]]] = None,
        forma_pagamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirma o processamento da nota com produtos mapeados
        Gera estoque e contas a pagar
        """
        from Entradas_Estoque.models import EntradaEstoque
        from contas_a_pagar.models import Titulospagar
        from Produtos.models import Produtos
        from Entidades.models import Entidades
        from django.db.models import Max, Q
        
        itens_processados = []
        itens_pendentes = []
        entrada_estoque = None
        titulos_criados = []
        
        try:
            with transaction.atomic(using=banco):
                # 2. Busca fornecedor
                fornecedor = None                    
                if nota_entrada.emitente_cnpj:
                    cnpj_limpo = re.sub(r'\D', '', nota_entrada.emitente_cnpj)
                elif nota_entrada.emitente_cpf:
                    cnpj_limpo = re.sub(r'\D', '', nota_entrada.emitente_cpf)
                else:
                    cnpj_limpo = ''
                fornecedor = Entidades.objects.using(banco).filter(
                    Q(enti_cnpj=cnpj_limpo) | Q(enti_cpf=cnpj_limpo),
                    enti_empr=int(nota_entrada.empresa)
                ).first()
                    
                if not fornecedor and len(cnpj_limpo) == 14:
                        cnpj_mask = f"{cnpj_limpo[0:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"
                        fornecedor = Entidades.objects.using(banco).filter(
                            Q(enti_cnpj=cnpj_mask) | Q(enti_cpf=cnpj_mask),
                            enti_empr=int(nota_entrada.empresa)
                        ).first()

                if not fornecedor:
                    fornecedor = EntradaNFeService._criar_fornecedor_da_nota(nota_entrada=nota_entrada, banco=banco)
                    if fornecedor:
                        try:
                            nota_entrada.cliente = int(getattr(fornecedor, "enti_clie", 0) or 0) or None
                            nota_entrada.save(using=banco)
                        except Exception:
                            pass

                if not fornecedor:
                    raise ValidationError("Fornecedor da nota não encontrado e não foi possível cadastrar automaticamente.")

                fornecedor_id = int(getattr(fornecedor, "enti_clie", 0) or 0)
                serie = str(getattr(nota_entrada, "serie", "") or "").strip() or "1"
                numero_nf = str(getattr(nota_entrada, "numero_nota_fiscal", "") or "").strip()
                if not numero_nf:
                    raise ValidationError("Número da nota não encontrado.")

                forma = (forma_pagamento or "").strip() or "54"
                if len(forma) != 2:
                    forma = "54"
                
                # 3. Processa cada item
                for idx, entrada in enumerate(entradas):
                    prod_cod = entrada.get('prod')
                    
                    if not prod_cod:
                        itens_pendentes.append({
                            'index': idx,
                            'forn_cod': entrada.get('forn_cod'),
                            'descricao': entrada.get('descricao', ''),
                            'motivo': 'Produto não informado'
                        })
                        continue
                    
                    # Busca produto
                    produto = Produtos.objects.using(banco).filter(
                        prod_codi=prod_cod,
                        prod_empr=str(nota_entrada.empresa)
                    ).first()
                    
                    if not produto:
                        itens_pendentes.append({
                            'index': idx,
                            'forn_cod': entrada.get('forn_cod'),
                            'descricao': entrada.get('descricao', ''),
                            'motivo': f'Produto {prod_cod} não encontrado'
                        })
                        continue
                    
                    # Prepara dados do item processado
                    item_processado = {
                        'produto': prod_cod,
                        'quantidade': entrada.get('quantidade', 0),
                        'valor_total': entrada.get('valor_total', 0),
                        'ean': entrada.get('ean'),
                        'forn_cod': entrada.get('forn_cod')
                    }
                    
                    itens_processados.append(item_processado)
                
                # 4. Gera entradas de estoque por item (modelo atual)
                entradas_criadas = []
                if itens_processados:
                    max_seq = EntradaEstoque.objects.using(banco).aggregate(max_sequ=Max('entr_sequ')).get('max_sequ') or 0
                    seq = int(max_seq)
                    fornecedor_id = fornecedor.enti_clie if fornecedor else None
                    for item in itens_processados:
                        seq += 1
                        e = EntradaEstoque.objects.using(banco).create(
                            entr_sequ=seq,
                            entr_empr=int(nota_entrada.empresa),
                            entr_fili=int(nota_entrada.filial),
                            entr_prod=str(item['produto']),
                            entr_enti=str(fornecedor_id) if fornecedor_id is not None else None,
                            entr_data=nota_entrada.data_emissao or date.today(),
                            entr_quan=Decimal(str(item['quantidade'] or 0)),
                            entr_tota=Decimal(str(item['valor_total'] or 0)),
                            entr_usua=int(usuario_id),
                            entr_obse=f"NF {nota_entrada.numero_nota_fiscal}"
                        )
                        entradas_criadas.append(e.entr_sequ)
                
                # 5. Gera contas a pagar
                valor_nota = float(nota_entrada.valor_total_nota or 0)
                
                # Busca duplicatas no XML
                duplicatas = duplicatas_override if duplicatas_override is not None else EntradaNFeService._extrair_duplicatas(nota_entrada.xml_nfe)
                
                if duplicatas:
                    # Cria título para cada duplicata
                    for idx_dup, dup in enumerate(duplicatas, start=1):
                        parc = str(dup.get('numero') or '').strip() or str(idx_dup)
                        existe_titulo = Titulospagar.objects.using(banco).filter(
                            titu_empr=int(nota_entrada.empresa),
                            titu_fili=int(nota_entrada.filial),
                            titu_forn=int(fornecedor_id),
                            titu_titu=str(nota_entrada.numero_nota_fiscal),
                            titu_seri=str(serie),
                            titu_parc=str(parc),
                        ).first()
                        if existe_titulo:
                            logger.warning(f"Título já existe para nota {nota_entrada.numero_nota_fiscal} parc={parc}")
                            return {
                                'status': 'titulo_existente',
                                'titulospagar': {
                                    'titu_titu': existe_titulo.titu_titu,
                                    'titu_seri': existe_titulo.titu_seri,
                                    'titu_parc': existe_titulo.titu_parc,
                                }
                            }
                        titulo = Titulospagar.objects.using(banco).create(
                            titu_empr=int(nota_entrada.empresa),
                            titu_fili=int(nota_entrada.filial),
                            titu_forn=int(fornecedor.enti_clie) if fornecedor else None,
                            titu_tipo='Entrada',  # Entrada
                            titu_titu=str(nota_entrada.numero_nota_fiscal),
                            titu_seri=str(serie),
                            titu_parc=str(parc),
                            titu_valo=dup['valor'],
                            titu_venc=dup['vencimento'],
                            titu_emis=nota_entrada.data_emissao or date.today(),
                            titu_aber='A',  # Aberto
                            titu_usua_lanc=usuario_id,
                            titu_form_reci=str(forma),
                            titu_hist=f"NF-e {nota_entrada.numero_nota_fiscal} - {dup['numero']}"
                        )
                        titulos_criados.append(titulo)
                else:
                    base_venc = nota_entrada.data_saida_entrada or nota_entrada.data_emissao or date.today()
                    parc = "1"
                    existe_titulo = Titulospagar.objects.using(banco).filter(
                        titu_empr=int(nota_entrada.empresa),
                        titu_fili=int(nota_entrada.filial),
                        titu_forn=int(fornecedor_id),
                        titu_titu=str(nota_entrada.numero_nota_fiscal),
                        titu_seri=str(serie),
                        titu_parc=str(parc),
                    ).first()
                    if existe_titulo:
                        logger.warning(f"Título já existe para nota {nota_entrada.numero_nota_fiscal}")
                        return {
                            'status': 'titulo_existente',
                            'titulospagar': {
                                'titu_titu': existe_titulo.titu_titu,
                                'titu_seri': existe_titulo.titu_seri,
                                'titu_parc': existe_titulo.titu_parc,
                            }
                        }
                    # Cria título único com valor total
                    titulo = Titulospagar.objects.using(banco).create(
                        titu_empr=int(nota_entrada.empresa),
                        titu_fili=int(nota_entrada.filial),
                        titu_forn=int(fornecedor.enti_clie) if fornecedor else None,
                        titu_tipo='Entrada',  # Entrada
                        titu_titu=str(nota_entrada.numero_nota_fiscal),
                        titu_seri=str(serie),
                        titu_parc=str(parc),
                        titu_valo=valor_nota,
                        titu_venc=base_venc,
                        titu_emis=nota_entrada.data_emissao or date.today(),
                        titu_aber='A',  # Aberto
                        titu_usua_lanc=usuario_id,
                        titu_form_reci=str(forma),
                        titu_hist=f"NF-e {nota_entrada.numero_nota_fiscal}"
                    )
                    titulos_criados.append(titulo)
                
                logger.info(f"{len(titulos_criados)} título(s) criado(s)")
                
                return {
                    'status': 'sucesso',
                    'entradas_estoque': entradas_criadas,
                    'titulos': [t.titu_titu for t in titulos_criados],
                    'itens_processados': len(itens_processados),
                    'itens_pendentes': itens_pendentes
                }
                
        except Exception as e:
            logger.exception(f"Erro ao confirmar processamento: {str(e)}")
            raise

    @staticmethod
    def _extrair_duplicatas(xml: str) -> List[Dict]:
        """Extrai duplicatas do XML da nota"""
        duplicatas = []
        
        try:
            root = ET.fromstring(xml)
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            for dup in root.findall('.//nfe:dup', ns):
                numero = dup.findtext('nfe:nDup', '', ns)
                vencimento = dup.findtext('nfe:dVenc', '', ns)
                valor = dup.findtext('nfe:vDup', '0', ns)
                
                try:
                    venc_date = datetime.strptime(vencimento, '%Y-%m-%d').date()
                except:
                    venc_date = date.today()
                
                duplicatas.append({
                    'numero': numero,
                    'vencimento': venc_date,
                    'valor': Decimal(valor)
                })
        except:
            pass
        
        return duplicatas

    @staticmethod
    def _criar_fornecedor_da_nota(*, nota_entrada, banco: str):
        from Entidades.models import Entidades
        from Entidades.utils import proxima_entidade

        empresa = int(getattr(nota_entrada, "empresa", 0) or 0)
        filial = int(getattr(nota_entrada, "filial", 0) or 0)
        if not empresa:
            return None

        cnpj = re.sub(r"\D", "", str(getattr(nota_entrada, "emitente_cnpj", "") or ""))
        cpf = re.sub(r"\D", "", str(getattr(nota_entrada, "emitente_cpf", "") or ""))
        doc = cnpj or cpf

        nome = (getattr(nota_entrada, "emitente_razao_social", "") or "").strip() or (getattr(nota_entrada, "emitente_nome_fantasia", "") or "").strip() or "FORNECEDOR"
        fant = (getattr(nota_entrada, "emitente_nome_fantasia", "") or "").strip() or nome
        ie = (getattr(nota_entrada, "emitente_ie", "") or "").strip() or None

        cep_raw = str(getattr(nota_entrada, "emitente_cep", "") or "")
        cep = re.sub(r"\D", "", cep_raw)[:8] or "00000000"
        ende = (getattr(nota_entrada, "emitente_logradouro", "") or "").strip()[:60] or "SEM ENDERECO"
        nume = (getattr(nota_entrada, "emitente_numero", "") or "").strip()[:10] or "S/N"
        bair = (getattr(nota_entrada, "emitente_bairro", "") or "").strip()[:60] or "CENTRO"
        cida = (getattr(nota_entrada, "emitente_nome_municipio", "") or "").strip()[:60] or "NAO INFORMADO"
        uf = (getattr(nota_entrada, "emitente_uf", "") or "").strip().upper()[:2] or "ZZ"
        fone = re.sub(r"\D", "", str(getattr(nota_entrada, "emitente_fone", "") or ""))[:14] or None

        if doc:
            qs = Entidades.objects.using(banco).filter(enti_empr=empresa)
            if len(doc) == 14:
                ex = qs.filter(enti_cnpj=doc).first()
            else:
                ex = qs.filter(enti_cpf=doc).first()
            if ex:
                return ex

        proximo = proxima_entidade(empresa, filial, banco)
        try:
            return Entidades.objects.using(banco).create(
                enti_empr=empresa,
                enti_clie=int(proximo),
                enti_nome=nome[:100],
                enti_tipo_enti="FO",
                enti_fant=fant[:100],
                enti_cnpj=doc if len(doc) == 14 else None,
                enti_cpf=doc if len(doc) == 11 else None,
                enti_insc_esta=ie[:14] if ie else None,
                enti_cep=cep,
                enti_ende=ende,
                enti_nume=nume,
                enti_cida=cida,
                enti_esta=uf,
                enti_bair=bair,
                enti_comp=None,
                enti_fone=fone,
                enti_emai=None,
                enti_tien="E",
                enti_situ="1",
            )
        except Exception:
            return None

    @staticmethod
    def _get_text(element, path: str, ns: dict = None, converter=None):
        """Extrai texto de elemento XML com conversão opcional"""
        if element is None:
            return None
        
        el = element.find(path, ns) if ns else element.find(path)
        
        if el is None or el.text is None:
            return None
        
        text = el.text.strip()
        
        if converter and text:
            try:
                return converter(text)
            except:
                return None
        
        return text if text else None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Converte string de data/datetime para date"""
        if not date_str:
            return None
        
        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S%z']:
            try:
                dt = datetime.strptime(date_str[:19], fmt[:10] if 'T' not in fmt else fmt[:19])
                return dt.date()
            except:
                continue
        
        return None
