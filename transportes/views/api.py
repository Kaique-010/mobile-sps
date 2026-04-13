from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from decimal import Decimal

from core.utils import get_licenca_db_config
from transportes.models import Cte, Mdfe, MdfeDocumento
from transportes.serializers.completo import CteCompletoSerializer
from transportes.serializers.mdfe import MdfeSerializer, MdfeDocumentoSerializer
from transportes.services.icms_service import ICMSCalculationService
from transportes.services.st_service import STService
from transportes.services.difal_service import DIFALService
from transportes.services.emissao_service import EmissaoService
from transportes.services.mdfe_emissao_service import MdfeEmissaoService
from transportes.services.mdfe_encerramento_service import MdfeEncerramentoService
from transportes.services.numeracao_service import NumeracaoMdfeService
from Entidades.models import Entidades
from Licencas.models import Filiais
from CFOP.models import CFOP

import logging

logger = logging.getLogger(__name__)

class CteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciamento completo de CT-e.
    Suporta atualização parcial por abas e ações de emissão.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'chave_acesso', 'destinatario__nome', 'remetente__nome']
    ordering_fields = ['id', 'numero', 'emissao', 'status']
    ordering = ['-id']

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return Cte.objects.using(slug).all()

    def get_serializer_class(self):
        return CteCompletoSerializer

    def perform_create(self, serializer):
        slug = get_licenca_db_config(self.request)
        serializer.save(using=slug)

    def perform_update(self, serializer):
        slug = get_licenca_db_config(self.request)
        serializer.save(using=slug)

    def perform_destroy(self, instance):
        slug = get_licenca_db_config(self.request)
        instance.delete(using=slug)

    @action(detail=True, methods=['post'], url_path='emitir')
    def emitir(self, request, pk=None):
        """
        Inicia o processo de emissão do CT-e.
        """
        slug = get_licenca_db_config(request)
        cte = self.get_object()
        
        try:
            # Emissão síncrona
            service = EmissaoService(cte, slug=slug)
            resultado = service.emitir()
            
            # Retorna 200 independente do status SEFAZ, pois a requisição HTTP foi OK
            # O status da nota vai no payload
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erro ao emitir CT-e: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='calcular-impostos')
    def calcular_impostos(self, request, pk=None):
        """
        Calcula impostos (ICMS, ST, DIFAL) baseado no CFOP e dados do CTe.
        Retorna JSON com os valores calculados.
        """
        return calcular_impostos_cte(request, pk)


class MdfeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["mdf_nume", "mdf_chav"]
    ordering_fields = ["mdf_id", "mdf_nume", "mdf_emis"]
    ordering = ["-mdf_id"]

    def get_queryset(self):
        slug = get_licenca_db_config(self.request)
        return Mdfe.objects.using(slug).all()

    def get_serializer_class(self):
        return MdfeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["banco"] = get_licenca_db_config(self.request)
        return context

    def perform_create(self, serializer):
        slug = get_licenca_db_config(self.request)
        empresa_id = getattr(self.request, "empresa", None) or 1
        filial_id = getattr(self.request, "filial", None) or 1

        from datetime import date

        serie = serializer.validated_data.get("mdf_seri") or 1
        numerador = NumeracaoMdfeService(empresa_id, filial_id, serie=serie, slug=slug)
        numero = numerador.proximo_numero()

        serializer.save(
            mdf_empr=empresa_id,
            mdf_fili=filial_id,
            mdf_seri=serie,
            mdf_nume=numero,
            mdf_emis=serializer.validated_data.get("mdf_emis") or date.today(),
            mdf_stat=0,
            mdf_canc=False,
            mdf_fina=False,
        )

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        slug = get_licenca_db_config(self.request)
        instance.delete(using=slug)

    @action(detail=True, methods=["post"], url_path="gerar-xml")
    def gerar_xml(self, request, pk=None):
        slug = get_licenca_db_config(request)
        mdfe = self.get_object()
        try:
            resultado = MdfeEmissaoService(mdfe, slug=slug).gerar_xml_assinado()
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erro ao gerar XML do MDF-e: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="emitir")
    def emitir(self, request, pk=None):
        """
        Emissão REST do MDF-e (gera XML assinado e chave de acesso).
        """
        return self.gerar_xml(request, pk=pk)

    @action(detail=True, methods=["post"], url_path="encerrar")
    def encerrar(self, request, pk=None):
        slug = get_licenca_db_config(request)
        mdfe = self.get_object()
        try:
            uf = (request.data.get("uf") or mdfe.mdf_esta_dest or "").strip()
            cmun = request.data.get("cmun") or request.data.get("municipio_id") or mdfe.mdf_cida_carr
            resultado = MdfeEncerramentoService(mdfe, slug=slug).encerrar(uf=uf, cmun=cmun)
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erro ao encerrar MDF-e: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="encerrar-automatico")
    def encerrar_automatico(self, request, pk=None):
        slug = get_licenca_db_config(request)
        mdfe = self.get_object()
        try:
            uf = (mdfe.mdf_esta_dest or "").strip()
            cmun = mdfe.mdf_cida_carr
            resultado = MdfeEncerramentoService(mdfe, slug=slug).encerrar(uf=uf, cmun=cmun)
            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Erro ao encerrar MDF-e (automático): {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["get", "post"], url_path="documentos")
    def documentos(self, request, pk=None):
        slug = get_licenca_db_config(request)
        mdfe = self.get_object()

        if request.method == "GET":
            qs = MdfeDocumento.objects.using(slug).filter(mdfe_id=mdfe.mdf_id).order_by("id")
            ser = MdfeDocumentoSerializer(qs, many=True, context={"banco": slug})
            return Response({"results": ser.data}, status=status.HTTP_200_OK)

        itens = request.data.get("documentos")
        if itens is None:
            itens = request.data.get("itens")
        if not isinstance(itens, list):
            return Response({"error": "Informe uma lista em 'documentos'."}, status=status.HTTP_400_BAD_REQUEST)

        ser = MdfeDocumentoSerializer(data=itens, many=True, context={"banco": slug})
        ser.is_valid(raise_exception=True)

        MdfeDocumento.objects.using(slug).filter(mdfe_id=mdfe.mdf_id).delete()
        objs = []
        for item in ser.validated_data:
            objs.append(
                MdfeDocumento(
                    mdfe_id=mdfe.mdf_id,
                    tipo_doc=item.get("tipo_doc"),
                    chave=item.get("chave"),
                    cmun_descarga=item.get("cmun_descarga"),
                    xmun_descarga=item.get("xmun_descarga"),
                )
            )
        MdfeDocumento.objects.using(slug).bulk_create(objs)

        qs = MdfeDocumento.objects.using(slug).filter(mdfe_id=mdfe.mdf_id).order_by("id")
        out = MdfeDocumentoSerializer(qs, many=True, context={"banco": slug})
        return Response({"results": out.data}, status=status.HTTP_200_OK)

# Funções auxiliares para uso em AJAX/Web

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from core.utils import get_licenca_db_config
from transportes.models import Cte
from Entidades.models import Entidades
import logging

logger = logging.getLogger(__name__)

@login_required
def get_cte_rota_info(request, pk, slug=None):
    """
    Retorna informações de rota (cidade/UF) baseada no remetente ou destinatário do CTe.
    """
    if not slug:
        slug = get_licenca_db_config(request)
        
    logger.info(f"API Rota Info: user={request.user} pk={pk} slug={slug}")
       
    cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
    
    tipo = request.GET.get('tipo') # remetente ou destinatario
    entidade_id = None
    
    if tipo == 'remetente':
        entidade_id = cte.remetente
    elif tipo == 'destinatario':
        entidade_id = cte.destinatario
    
    logger.info(f"API Rota Info: tipo={tipo} entidade_id={entidade_id}")
        
    if not entidade_id:
        return JsonResponse({'error': 'Entidade não vinculada ao CTe.'}, status=400)
        
    entidade = Entidades.objects.using(slug).filter(pk=entidade_id).first()
    
    if not entidade:
        logger.warning(f"API Rota Info: Entidade {entidade_id} não encontrada no banco {slug}")
        return JsonResponse({'error': 'Entidade não encontrada.'}, status=404)
        
    return JsonResponse({
        'cidade_id': entidade.enti_codi_cida,
        'cidade_nome': entidade.enti_cida,
        'uf': entidade.enti_esta
    })

@login_required
def get_mdfe_proximo_numero(request, slug=None):
    slug = get_licenca_db_config(request) or slug
    empresa_id = request.session.get("empresa_id")
    filial_id = request.session.get("filial_id") or 1
    serie_raw = request.GET.get("serie") or request.GET.get("mdf_seri") or 1
    try:
        serie = int(str(serie_raw).strip() or 1)
    except Exception:
        serie = 1

    if not empresa_id:
        return JsonResponse({"error": "Empresa não encontrada na sessão."}, status=400)

    numerador = NumeracaoMdfeService(empresa_id, filial_id, serie=serie, slug=slug)
    numero = numerador.proximo_numero()
    return JsonResponse({"serie": serie, "numero": numero})


@login_required(login_url='/web/login/')
def calcular_impostos_cte(request, pk, slug=None):
    """
    Calcula impostos do CTe baseado no CFOP informado.
    """
    slug = get_licenca_db_config(request)
    cte = get_object_or_404(Cte.objects.using(slug), pk=pk)
    
    cfop_id = request.GET.get('cfop')
    if not cfop_id:
        return JsonResponse({'error': 'CFOP não informado.'}, status=400)
        
    # Busca CFOP
    cfop = CFOP.objects.using(slug).filter(pk=cfop_id).first()
        
    if not cfop:
        return JsonResponse({'error': 'CFOP não encontrado.'}, status=404)

    # Prepara dados para cálculo
    try:
        # Adapters (Reutilizados do Form/Serializer logic)
        class ServiceEmpresaAdapter:
            def __init__(self, simples, db_alias='default'):
                self.simples_nacional = simples
                self._state = type('State', (), {'db': db_alias})
        
        class ServiceOperacaoAdapter:
            def __init__(self, uf_orig, uf_dest, contrib):
                self.uf_origem = uf_orig
                self.uf_destino = uf_dest
                self.contribuinte = contrib

        # Busca dados necessários
        filial = Filiais.objects.using(slug).filter(pk=cte.filial).first()
        simples_nacional = str(filial.empr_regi_trib) == '1' if filial else False
        
        remetente = Entidades.objects.using(slug).filter(pk=cte.remetente).first()
        destinatario = Entidades.objects.using(slug).filter(pk=cte.destinatario).first()
        
        # Mapeamento de Código IBGE para UF
        CODIGO_UF_PARA_SIGLA = {
            '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
            '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
            '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
            '41': 'PR', '42': 'SC', '43': 'RS',
            '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
        }

        def get_uf_from_ibge(ibge_code):
            if not ibge_code: return None
            s_code = str(ibge_code).strip()
            if len(s_code) < 2: return None
            prefix = s_code[:2]
            return CODIGO_UF_PARA_SIGLA.get(prefix)

        # Prioriza UFs da rota (Coleta/Entrega) se disponíveis
        uf_origem = get_uf_from_ibge(cte.cidade_coleta)
        uf_destino = get_uf_from_ibge(cte.cidade_entrega)

        # Fallback para UFs das entidades se não encontrar na rota
        if not uf_origem and remetente:
            uf_origem = remetente.enti_esta
        
        if not uf_destino and destinatario:
            uf_destino = destinatario.enti_esta
            
        if not uf_origem or not uf_destino:
             logger.error(f"Erro cálculo impostos CTE {pk}: UFs não identificadas. Orig: {uf_origem}, Dest: {uf_destino}")
             return JsonResponse({'error': 'Não foi possível identificar UFs de origem e destino (Rota ou Entidades).'}, status=400)
             
        # Verifica se destinatário é contribuinte
        ie_dest = destinatario.enti_insc_esta if destinatario else None
        # Normaliza IE para verificação
        ie_dest_clean = ie_dest.strip().upper() if ie_dest else ''
        contribuinte = bool(ie_dest and ie_dest_clean not in ['ISENTO', 'ISENTA', '', 'NONE'])
        
        # LOGGING PARA DEBUG
        logger.info(f"=== CÁLCULO IMPOSTOS CTE {pk} ===")
        logger.info(f"CFOP: {cfop.cfop_codi} (ID: {cfop.pk})")
        logger.info(f"Origem: {uf_origem} | Destino: {uf_destino}")
        logger.info(f"Simples Nacional: {simples_nacional}")
        logger.info(f"Destinatário: {destinatario.enti_nome if destinatario else 'N/A'} (IE: {ie_dest}) -> Contribuinte: {contribuinte}")

        empresa_adapter = ServiceEmpresaAdapter(simples_nacional, slug)
        operacao_adapter = ServiceOperacaoAdapter(uf_origem, uf_destino, contribuinte)
        
        # Base de Cálculo (Total do Serviço)
        # Prioriza frete_valor, fallback para total_valor
        base_calculo = cte.frete_valor or cte.total_valor or Decimal('0.00')
        logger.info(f"Base Cálculo: {base_calculo}")
        
        response_data = {}
        
        # 1. ICMS
        icms_calculado_valor = Decimal('0.00')
        if cfop.cfop_exig_icms:
            icms_service = ICMSCalculationService(empresa_adapter, operacao_adapter)
            res_icms = icms_service.calcular(base_calculo, cfop)
            
            logger.info(f"Resultado ICMS: {res_icms}")

            if res_icms:
                response_data.update({
                    'cst_icms': res_icms['cst'],
                    'aliq_icms': res_icms['aliquota'],
                    'valor_icms': res_icms['valor'],
                    'reducao_icms': res_icms['reducao'],
                    'base_icms': res_icms['base']
                })
                icms_calculado_valor = res_icms['valor']
            else:
                logger.warning(f"Nenhuma regra de ICMS encontrada para CFOP {cfop.cfop_codi}, UF {uf_origem}->{uf_destino}, Contrib {contribuinte}")
                
        # 2. ST
        if cfop.cfop_gera_st:
            st_service = STService(empresa_adapter, operacao_adapter)
            res_st = st_service.calcular(base_calculo, icms_calculado_valor, cfop)
            
            if res_st:
                response_data.update({
                    'base_icms_st': res_st['base_st'],
                    'valor_icms_st': res_st['valor_st'],
                    'aliquota_icms_st': res_st['aliquota_st'],
                    'margem_valor_adicionado_st': res_st['mva_st']
                })

        # 3. DIFAL
        if cfop.cfop_gera_difal:
            difal_service = DIFALService(empresa_adapter, operacao_adapter)
            res_difal = difal_service.calcular(base_calculo, icms_calculado_valor, cfop)
            
            if res_difal:
                response_data.update({
                    'valor_bc_uf_dest': res_difal['base_difal'],
                    'valor_icms_uf_dest': res_difal['valor_difal'],
                    'aliquota_interestadual': res_difal['aliquota_interestadual'],
                    'aliquota_interna_dest': res_difal['aliquota_destino']
                })
                
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Erro ao calcular impostos via API: {e}")
        return JsonResponse({'error': f"Erro interno ao calcular impostos: {str(e)}"}, status=500)
