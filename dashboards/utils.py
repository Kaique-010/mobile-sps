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


def enviar_whatsapp(numero, dados):
    print(f"Enviando WhatsApp para {numero} com dados: {dados}")
    return True