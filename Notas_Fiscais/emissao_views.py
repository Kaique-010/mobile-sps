"""
Views para emissão de notas fiscais
"""
import logging
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import viewsets

from .models import NotaFiscal
from .serializers import NotaFiscalSerializer
from .emissao_service import EmissaoNFeService
from core.utils import get_licenca_db_config

logger = logging.getLogger(__name__)


class EmissaoNFeViewSet(viewsets.ViewSet):
    """ViewSet para emissão de NFe"""
    
    def _get_emissao_service(self, request):
        """Obtém instância do serviço de emissão configurado"""
        # Configurações do certificado (devem vir das configurações da empresa)
        certificado_path = getattr(settings, 'NFE_CERTIFICADO_PATH', '')
        senha_certificado = getattr(settings, 'NFE_CERTIFICADO_SENHA', '')
        uf = getattr(settings, 'NFE_UF', 'PR')
        homologacao = getattr(settings, 'NFE_HOMOLOGACAO', True)
        
        if not certificado_path or not senha_certificado:
            raise ValidationError({
                'error': 'Certificado digital não configurado'
            })
        
        return EmissaoNFeService(
            certificado_path=certificado_path,
            senha_certificado=senha_certificado,
            uf=uf,
            homologacao=homologacao
        )
    
    @action(detail=False, methods=['get'])
    def status_servico(self, request):
        """Verifica status do serviço da SEFAZ"""
        try:
            service = self._get_emissao_service(request)
            response = service.verificar_status_servico()
            
            return Response({
                'status': 'online',
                'resposta_sefaz': response.text
            })
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do serviço: {e}")
            return Response({
                'error': f'Erro ao verificar status: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def emitir(self, request):
        """Emite uma nova NFe"""
        try:
            dados = request.data
            
            # Validar dados obrigatórios
            campos_obrigatorios = [
                'dados_nfe', 'dados_emitente', 'dados_cliente', 'itens'
            ]
            
            for campo in campos_obrigatorios:
                if campo not in dados:
                    raise ValidationError({
                        'error': f'Campo obrigatório: {campo}'
                    })
            
            # Obter banco da licença
            banco = get_licenca_db_config(request)
            if not banco:
                raise ValidationError({
                    'error': 'Configuração de banco não encontrada'
                })
            
            with transaction.atomic(using=banco):
                # Verificar se número já existe
                numero_nf = dados['dados_nfe']['numero']
                serie = dados['dados_nfe'].get('serie', 1)
                empresa = dados['dados_nfe'].get('empresa')
                filial = dados['dados_nfe'].get('filial')
                
                if NotaFiscal.objects.using(banco).filter(
                    empresa=empresa,
                    filial=filial,
                    serie=serie,
                    numero_nota_fiscal=numero_nf
                ).exists():
                    raise ValidationError({
                        'error': f'Nota fiscal {serie}-{numero_nf} já existe'
                    })
                
                # Emitir NFe
                service = self._get_emissao_service(request)
                resultado = service.emitir_nfe(
                    dados_nfe=dados['dados_nfe'],
                    dados_emitente=dados['dados_emitente'],
                    dados_cliente=dados['dados_cliente'],
                    itens=dados['itens']
                )
                
                if resultado['sucesso']:
                    # Salvar NFe no banco
                    nota_fiscal_data = {
                        'empresa': empresa,
                        'filial': filial,
                        'numero_nota_fiscal': numero_nf,
                        'serie': str(serie),
                        'modelo': dados['dados_nfe'].get('modelo', '55'),
                        'chave_acesso': resultado['chave_acesso'],
                        'protocolo_nfe': resultado['protocolo'],
                        'xml_nfe': resultado['xml_autorizado'],
                        'data_emissao': dados['dados_nfe'].get('data_emissao'),
                        'natureza_operacao': dados['dados_nfe']['natureza_operacao'],
                        'status_nfe': resultado['status'],
                        'ambiente': 2 if service.homologacao else 1,
                        'emitente_cnpj': dados['dados_emitente']['cnpj'],
                        'emitente_razao_social': dados['dados_emitente']['razao_social'],
                        'destinatario_cnpj': dados['dados_cliente'].get('cnpj'),
                        'destinatario_cpf': dados['dados_cliente'].get('cpf'),
                        'destinatario_razao_social': dados['dados_cliente']['razao_social']
                    }
                    
                    # Calcular valor total dos itens
                    valor_total = sum(float(item['valor_total']) for item in dados['itens'])
                    nota_fiscal_data['valor_total_nota'] = valor_total
                    
                    serializer = NotaFiscalSerializer(data=nota_fiscal_data)
                    if serializer.is_valid():
                        nota_fiscal = serializer.save()
                        
                        return Response({
                            'sucesso': True,
                            'nota_fiscal': NotaFiscalSerializer(nota_fiscal).data,
                            'chave_acesso': resultado['chave_acesso'],
                            'protocolo': resultado['protocolo'],
                            'status': resultado['status'],
                            'motivo': resultado['motivo']
                        }, status=status.HTTP_201_CREATED)
                    else:
                        logger.error(f"Erro na validação: {serializer.errors}")
                        return Response({
                            'sucesso': False,
                            'erro': 'NFe emitida mas erro ao salvar no banco',
                            'detalhes': serializer.errors,
                            'chave_acesso': resultado['chave_acesso']
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response({
                        'sucesso': False,
                        'status': resultado.get('status'),
                        'motivo': resultado.get('motivo'),
                        'erro': resultado.get('erro')
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao emitir NFe: {e}")
            return Response({
                'error': f'Erro interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def consultar(self, request):
        """Consulta situação de uma NFe"""
        try:
            chave_acesso = request.data.get('chave_acesso')
            if not chave_acesso:
                raise ValidationError({
                    'error': 'Chave de acesso é obrigatória'
                })
            
            service = self._get_emissao_service(request)
            resultado = service.consultar_nfe(chave_acesso)
            
            return Response(resultado)
            
        except Exception as e:
            logger.error(f"Erro ao consultar NFe: {e}")
            return Response({
                'error': f'Erro ao consultar: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def cancelar(self, request):
        """Cancela uma NFe autorizada"""
        try:
            dados = request.data
            campos_obrigatorios = ['chave_acesso', 'protocolo', 'justificativa']
            
            for campo in campos_obrigatorios:
                if campo not in dados:
                    raise ValidationError({
                        'error': f'Campo obrigatório: {campo}'
                    })
            
            # Validar justificativa (mínimo 15 caracteres)
            if len(dados['justificativa']) < 15:
                raise ValidationError({
                    'error': 'Justificativa deve ter no mínimo 15 caracteres'
                })
            
            service = self._get_emissao_service(request)
            resultado = service.cancelar_nfe(
                chave_acesso=dados['chave_acesso'],
                protocolo=dados['protocolo'],
                justificativa=dados['justificativa']
            )
            
            if resultado['sucesso']:
                # Atualizar status no banco
                banco = get_licenca_db_config(request)
                if banco:
                    try:
                        nota_fiscal = NotaFiscal.objects.using(banco).get(
                            chave_acesso=dados['chave_acesso']
                        )
                        nota_fiscal.cancelada = True
                        nota_fiscal.protocolo_cancelamento = resultado['protocolo_cancelamento']
                        nota_fiscal.data_cancelamento = resultado['data_cancelamento']
                        nota_fiscal.justificativa_cancelamento = dados['justificativa']
                        nota_fiscal.save()
                    except NotaFiscal.DoesNotExist:
                        logger.warning(f"NFe não encontrada no banco: {dados['chave_acesso']}")
            
            return Response(resultado)
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao cancelar NFe: {e}")
            return Response({
                'error': f'Erro ao cancelar: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def proximo_numero(self, request):
        """Obtém o próximo número disponível para NFe"""
        try:
            empresa = request.query_params.get('empresa')
            filial = request.query_params.get('filial')
            serie = request.query_params.get('serie', '1')
            
            if not empresa or not filial:
                raise ValidationError({
                    'error': 'Empresa e filial são obrigatórios'
                })
            
            banco = get_licenca_db_config(request)
            if not banco:
                raise ValidationError({
                    'error': 'Configuração de banco não encontrada'
                })
            
            # Buscar último número usado
            ultima_nota = NotaFiscal.objects.using(banco).filter(
                empresa=empresa,
                filial=filial,
                serie=serie
            ).order_by('-numero_nota_fiscal').first()
            
            proximo_numero = 1
            if ultima_nota:
                proximo_numero = ultima_nota.numero_nota_fiscal + 1
            
            return Response({
                'proximo_numero': proximo_numero,
                'empresa': empresa,
                'filial': filial,
                'serie': serie
            })
            
        except Exception as e:
            logger.error(f"Erro ao obter próximo número: {e}")
            return Response({
                'error': f'Erro interno: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)