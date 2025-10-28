"""
Exemplo de uso do EmissaoNFeService com modelos Django
"""
from datetime import datetime
from decimal import Decimal
from .emissao_service import EmissaoNFeService

# Exemplo de uso com modelos Django
def exemplo_emissao_nfe():
    """Exemplo de como usar o serviço de emissão com modelos Django"""
    
    # Configurar o serviço
    service = EmissaoNFeService(
        certificado_path='/caminho/para/certificado.pfx',
        senha_certificado='senha_do_certificado',
        uf='PR',
        homologacao=True  # True para homologação, False para produção
    )
    
    # Dados da NFe
    dados_nfe = {
        'numero': 1,
        'serie': 1,
        'natureza_operacao': 'Venda de mercadoria',
        'data_emissao': datetime.now(),
        'data_saida_entrada': datetime.now(),
        'tipo_documento': 1,  # 1=Saída
        'forma_pagamento': 0,  # 0=À vista
        'tipo_pagamento': 1,   # 1=Dinheiro
        'modelo': 55,
        'municipio_ocorrencia': 'Curitiba',
        'tipo_impressao_danfe': 1,
        'forma_emissao': 1,
        'cliente_final': 1,
        'indicador_destino': 1,
        'indicador_presenca': 1,
        'finalidade_emissao': 1,
        'processo_emissao': 0,
        'modalidade_frete': 9
    }
    
    # Itens da NFe
    itens = [
        {
            'codigo': 'PROD001',
            'descricao': 'Produto de Teste',
            'ncm': '12345678',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 1,
            'valor_unitario': Decimal('100.00'),
            'valor_total': Decimal('100.00'),
            'origem': 0,
            'modalidade_icms': 102,
            'valor_icms': Decimal('0.00'),
            'valor_ipi': Decimal('0.00'),
            'valor_pis': Decimal('0.00'),
            'valor_cofins': Decimal('0.00')
        }
    ]
    
    # IDs dos modelos Django
    filial_id = 1  # ID da filial emitente
    entidade_id = 1  # ID da entidade destinatária
    
    # Emitir NFe usando os modelos Django
    resultado = service.emitir_nfe_com_modelos(
        dados_nfe=dados_nfe,
        filial_id=filial_id,
        entidade_id=entidade_id,
        itens=itens
    )
    
    if resultado['sucesso']:
        print(f"NFe emitida com sucesso!")
        print(f"Chave de acesso: {resultado['chave_acesso']}")
        print(f"Protocolo: {resultado['protocolo']}")
        print(f"Emitente: {resultado['filial']}")
        print(f"Destinatário: {resultado['destinatario']}")
    else:
        print(f"Erro na emissão: {resultado.get('erro', resultado.get('motivo'))}")
    
    return resultado

# Exemplo de consulta de NFe
def exemplo_consulta_nfe():
    """Exemplo de como consultar uma NFe"""
    
    service = EmissaoNFeService(
        certificado_path='/caminho/para/certificado.pfx',
        senha_certificado='senha_do_certificado',
        uf='PR',
        homologacao=True
    )
    
    chave_acesso = '41230714200166000187550010000000011123456789'
    
    resultado = service.consultar_nfe(chave_acesso)
    
    print(f"Status: {resultado['status']}")
    print(f"Motivo: {resultado['motivo']}")
    
    return resultado

# Exemplo de cancelamento de NFe
def exemplo_cancelamento_nfe():
    """Exemplo de como cancelar uma NFe"""
    
    service = EmissaoNFeService(
        certificado_path='/caminho/para/certificado.pfx',
        senha_certificado='senha_do_certificado',
        uf='PR',
        homologacao=True
    )
    
    chave_acesso = '41230714200166000187550010000000011123456789'
    protocolo = '141230000000001'
    justificativa = 'Cancelamento por erro na emissão'
    
    resultado = service.cancelar_nfe(
        chave_acesso=chave_acesso,
        protocolo=protocolo,
        justificativa=justificativa
    )
    
    if resultado['sucesso']:
        print(f"NFe cancelada com sucesso!")
        print(f"Protocolo de cancelamento: {resultado['protocolo_cancelamento']}")
    else:
        print(f"Erro no cancelamento: {resultado['motivo']}")
    
    return resultado

if __name__ == '__main__':
    # Executar exemplo
    exemplo_emissao_nfe()