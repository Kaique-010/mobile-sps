import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from ..serializers import (
    NotaFiscalEntradaSerializer,
    ImportarNotasDestinadasSerializer,
)
from ..services.notas_destinadas_service import NotasDestinadasService
from ..services.entrada_nfe_service import EntradaNFeService
from ..services.manifestacao_service import ManifestacaoService
from core.utils import get_licenca_db_config
from Licencas.models import Filiais
from Licencas.crypto import decrypt_bytes, decrypt_str
import os
import tempfile

logger = logging.getLogger(__name__)


class ImportarNotasDestinadasView(APIView):
    """
    POST /api/<slug>/nfe/importar-notas-destinadas/

    Dispara:
    - consulta DF-e
    - registra entradas
    - (opcional) manifesta ciência da operação
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ImportarNotasDestinadasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        banco = get_licenca_db_config(request)

        uf = data['uf']
        cnpj = data['cnpj']
        ultimo_nsu = data['ultimo_nsu']
        caminho_pfx = data['caminho_pfx']
        senha_pfx = data['senha_pfx']
        ambiente = data['ambiente']
        empresa = data['empresa']
        filial = data['filial']
        cliente = data.get('cliente')
        gerar_estoque = data['gerar_estoque']
        gerar_contas_pagar = data['gerar_contas_pagar']
        manifestar_ciencia = data['manifestar_ciencia']

        try:
            pfx_path = (caminho_pfx or '').strip()
            if pfx_path.startswith('~'):
                pfx_path = os.path.expanduser(pfx_path)
            if pfx_path:
                pfx_path = os.path.normpath(pfx_path)
            if not pfx_path or not os.path.isfile(pfx_path):
                try:
                    f2 = Filiais.objects.using(banco).filter(empr_empr=int(filial), empr_codi=int(empresa)).first()
                except Exception:
                    f2 = None
                if f2:
                    try:
                        if not senha_pfx and f2.empr_senh_cert:
                            try:
                                senha_pfx = decrypt_str(f2.empr_senh_cert)
                            except Exception:
                                senha_pfx = senha_pfx
                        token = f2.empr_cert_digi
                        data_bytes = None
                        if token:
                            if isinstance(token, memoryview):
                                token = token.tobytes()
                            elif isinstance(token, bytearray):
                                token = bytes(token)
                            elif isinstance(token, str):
                                token = token.encode('utf-8')
                            try:
                                data_bytes = decrypt_bytes(token)
                            except Exception:
                                data_bytes = None
                            if not data_bytes:
                                try:
                                    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
                                    load_key_and_certificates(token, (senha_pfx or '').encode('utf-8'))
                                    data_bytes = token
                                except Exception:
                                    data_bytes = None
                            if data_bytes:
                                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pfx')
                                tmp.write(data_bytes)
                                tmp.flush()
                                tmp.close()
                                pfx_path = tmp.name
                    except Exception:
                        pfx_path = pfx_path
            if not pfx_path or not os.path.isfile(pfx_path):
                return Response({'error': 'Certificado A1 (pfx) não encontrado. Verifique se há certificado binário cadastrado na Filial ou informe o caminho válido.'}, status=status.HTTP_400_BAD_REQUEST)
            if not senha_pfx:
                return Response({'error': 'Senha do certificado A1 é obrigatória.'}, status=status.HTTP_400_BAD_REQUEST)
            xmls, novo_ultimo_nsu = NotasDestinadasService.consultar_notas_destinadas(
                uf=uf,
                cnpj=cnpj,
                ultimo_nsu=ultimo_nsu,
                caminho_pfx=pfx_path,
                senha_pfx=senha_pfx,
                ambiente=ambiente,
            )
        except Exception as e:
            logger.exception(f'Erro ao consultar DF-e: {e}')
            return Response({'error': 'Falha ao consultar DF-e.'}, status=status.HTTP_400_BAD_REQUEST)

        notas_criadas = []

        for xml in xmls:
            entrada = EntradaNFeService.registrar_entrada(
                xml=xml,
                empresa=empresa,
                filial=filial,
                cliente=cliente,
                gerar_estoque=gerar_estoque,
                gerar_contas_pagar=gerar_contas_pagar,
                banco=banco,
                usuario_id=getattr(request.user, 'usua_codi', 0),
            )
            notas_criadas.append(entrada)

            if manifestar_ciencia:
                try:
                    ManifestacaoService.manifestar_ciencia(
                        nota_entrada=entrada,
                        uf=uf,
                        cnpj_destinatario=cnpj,
                        caminho_pfx=pfx_path,
                        senha_pfx=senha_pfx,
                        ambiente=ambiente,
                    )
                except Exception as e:
                    logger.exception(f'Erro ao manifestar ciência para NF-e {entrada.id}: {e}')

        resp = {
            'mensagem': 'Importação concluída',
            'quantidade_xmls': len(xmls),
            'novo_ultimo_nsu': novo_ultimo_nsu,
            'notas_criadas': NotaFiscalEntradaSerializer(notas_criadas, many=True, context={'banco': banco}).data,
        }
        return Response(resp, status=status.HTTP_201_CREATED)
