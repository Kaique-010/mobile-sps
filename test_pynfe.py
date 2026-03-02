
try:
    from pynfe.processamento.comunicacao import ComunicacaoSefaz
    print("MÉTODOS DE ComunicacaoSefaz:")
    print([m for m in dir(ComunicacaoSefaz) if not m.startswith('_')])
except ImportError:
    print("Não foi possível importar ComunicacaoSefaz. Tentando pynfe.processamento.comunicacao...")
    try:
        import pynfe.processamento.comunicacao as com
        print("MÓDULO pynfe.processamento.comunicacao:")
        print(dir(com))
    except Exception as e:
        print(f"Erro: {e}")

# Tentar encontrar onde está a classe
import pynfe
print(f"\nPyNFe path: {pynfe.__file__}")
