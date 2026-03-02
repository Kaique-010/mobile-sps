import os
import sys
import django
from django.db import transaction

# Setup Django
sys.path.append(r'd:\mobile-sps')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SPS_ERP.settings')
django.setup()

from Notas_Fiscais.services.nota_service import NotaService
from Notas_Fiscais.dominio.builder import NotaBuilder
from Notas_Fiscais.emissao.gerador_xml import GeradorXML
from Licencas.models import Filiais
from Entidades.models import Entidades
from Notas_Fiscais.models import Nota
from Produtos.models import Produtos

@transaction.atomic
def run_verification():
    print("Iniciando verificação...")
    
    # 1. Encontrar ou criar uma filial de teste
    # Vamos pegar a primeira filial existente e modificar temporariamente o ambiente na memória (ou no banco e rollback)
    filial_obj = Filiais.objects.first()
    if not filial_obj:
        print("ERRO: Nenhuma filial encontrada para teste.")
        return

    print(f"Filial encontrada: {filial_obj.empr_nome} (Original ambiente: {filial_obj.empr_ambi_nfe})")
    
    # Forçar ambiente para 1 (Produção) para o teste
    original_ambiente = filial_obj.empr_ambi_nfe
    filial_obj.empr_ambi_nfe = 1
    filial_obj.save()
    print("Ambiente da filial alterado para 1 (Produção) para teste.")

    # 2. Encontrar um destinatário e produto para o teste
    destinatario = Entidades.objects.filter(enti_empr=filial_obj.empr_empr).first()
    if not destinatario:
        print("ERRO: Nenhum destinatário encontrado.")
        raise Exception("Rollback")
        
    produto = Produtos.objects.filter(prod_empr=filial_obj.empr_empr).first()
    if not produto:
        print("ERRO: Nenhum produto encontrado.")
        raise Exception("Rollback")

    # 3. Criar payload para NotaService
    data = {
        "destinatario": destinatario.enti_clie,
        "modelo": "55",
        "serie": "1",
        "numero": 0,
        "tipo_operacao": 1,
        "finalidade": 1,
        "natureza_operacao": "VENDA",
    }
    
    itens = [{
        "produto_id": produto.prod_codi,
        "quantidade": 1,
        "unitario": 10.0,
        "cfop": "5102",
        "ncm": "12345678",
        "cst_icms": "00",
        "cst_pis": "01",
        "cst_cofins": "01",
        "unidade": "UN",
        "descricao": "PRODUTO TESTE"
    }]

    try:
        # 4. Chamar NotaService.criar
        print("Criando nota via NotaService...")
        nota = NotaService.criar(
            data=data,
            itens=itens,
            impostos_map=None,
            transporte=None,
            empresa=filial_obj.empr_empr,
            filial=filial_obj.empr_codi
        )
        
        print(f"Nota criada. ID: {nota.id}, Ambiente na Nota: {nota.ambiente}")
        
        if nota.ambiente != 1:
            print("FALHA: O ambiente na nota deveria ser 1, mas é", nota.ambiente)
        else:
            print("SUCESSO: O ambiente na nota foi gravado corretamente como 1.")

        # 5. Gerar XML
        print("Gerando DTO e XML...")
        dto_obj = NotaBuilder(nota).build()
        dto_dict = dto_obj.dict()
        
        # Adicionar chave fictícia para o gerador não reclamar
        dto_dict["chave"] = "35230112345678000199550010000000011000000000"
        dto_dict["cNF"] = "00000001"
        
        xml = GeradorXML().gerar(dto_dict)
        
        # 6. Verificar XML
        if "<tpAmb>1</tpAmb>" in xml:
            print("SUCESSO: Tag <tpAmb>1</tpAmb> encontrada no XML.")
        else:
            print("FALHA: Tag <tpAmb>1</tpAmb> NÃO encontrada no XML.")
            print("XML Parcial:", xml[:500])

        if "<cMunFG>" in xml:
             print("SUCESSO: Tag <cMunFG> encontrada no XML.")
        else:
             print("FALHA: Tag <cMunFG> NÃO encontrada no XML.")

        if "<cDV>" in xml:
             print("SUCESSO: Tag <cDV> encontrada no XML.")
        else:
             print("FALHA: Tag <cDV> NÃO encontrada no XML.")
             
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Sempre fazer rollback
        print("Fazendo rollback das alterações...")
        raise Exception("Fim do teste (Rollback intencional)")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        if str(e) == "Fim do teste (Rollback intencional)":
            print("Teste concluído.")
        else:
            print(f"Erro inesperado: {e}")
