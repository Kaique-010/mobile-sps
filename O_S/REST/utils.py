from django.core.mail import send_mail
from django.conf import settings

def enviar_email(email, dados):
    assunto = 'Relatório de Dados'
    mensagem = formatar_mensagem(dados) 
    remetente = settings.DEFAULT_FROM_EMAIL
    destinatarios = [email]

    try:
        send_mail(
            assunto,
            mensagem,
            remetente,
            destinatarios,
            fail_silently=False,
        )
        print(f"E-mail enviado para {email}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False


def formatar_mensagem(dados):
   
    linhas = []
    for chave, valor in dados.items():
        linhas.append(f"{chave}: {valor}")
    return "\n".join(linhas)


def enviar_whatsapp(cliente_id, dados):
    """
    Busca o contato do cliente na Entidade e envia mensagem de WhatsApp.
    :param cliente_id: ID do cliente (enti_clie) associado à OS
    :param dados: Dicionário com os dados a serem enviados
    :return: (bool, str) - Sucesso/Falha e mensagem
    """
    from Entidades.models import Entidades
    
    try:
        entidade = Entidades.objects.get(enti_clie=cliente_id)
        # Prioriza celular, se não tiver usa o telefone fixo
        numero = entidade.enti_celu or entidade.enti_fone
        
        if not numero:
            print(f"Cliente {cliente_id} ({entidade.enti_nome}) não possui número cadastrado.")
            return False, f"Cliente {entidade.enti_nome} não possui celular/telefone cadastrado."
            
        print(f"Enviando WhatsApp para {numero} (Cliente: {entidade.enti_nome}) com dados: {dados}")
        # Aqui entraria a integração real com a API de WhatsApp
        return True, "WhatsApp enviado com sucesso."
        
    except Entidades.DoesNotExist:
        print(f"Cliente {cliente_id} não encontrado na base de dados.")
        return False, f"Cliente {cliente_id} não encontrado."
    except Exception as e:
        print(f"Erro ao processar envio de WhatsApp: {e}")
        return False, f"Erro ao processar envio: {str(e)}"
