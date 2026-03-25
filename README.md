📱 Guia de Configuração: Mobile-SPS
Primeiramente, deve se ter acesso ao repositório do projeto.
solicitando acesso para: https://github.com/spartacusWeb25/mobile-sps

Após a persmissão de acesso ao repositório, clone o projeto para sua máquina local:

Bash
git clone https://github.com/spartacusWeb25/mobile-sps.git
cd mobile-sps

é necessário instalar as dependências do projeto:

primeiro:
Ter o python instalado na versão minima de 3.11

instale em o python em: https://www.python.org/downloads/

depois de instalado.

inicie um ambiente virtual para o projeto:

inicie um terminal na pasta do projeto com ctrl + shift + '

Crie o ambiente virtual:

Bash/terminal
python -m venv venv

e o ative com:
source venv/bin/activate

crie um arquivo .env na raiza do projeto com as variáveis a serem definidas pelo responsável do projeto:

# Variáveis de Ambiente

exemplo:

SECRET_KEY=senha_aqui
DEBUG=False
USE_LOCAL_DB=True
LOCAL_DB_NAME=savexml***
LOCAL_DB_USER=savexml***
LOCAL_DB_PASSWORD=sua_senha_aqui

então instale as dependências do projeto contidas em requirements.txt

Bash/terminal
pip install -r requirements.txt

Feito este primeiro passo, você está pronto para configurar o ambiente de desenvolvimento.

Este documento a seguir detalha o processo de criação de novas bases, configuração do servidor (Gunicorn/Nginx), acesso SSH e automação de Deploy.

1. Configuração de Novas Bases (Mobile)
   Para adicionar uma nova empresa/base ao sistema, siga os passos abaixo:

1.1 Inserir nova base no Savexml1, na tabela de licencasweb
Acesse o save rodando o projeto com:

Bash/terminal
python manage.py runserver

Então acesso o sistema com os dados:
documento: 13446907000120
usuario: mobile
senha: padrão do sistema

após o acesso, selecione a seguinte url:

http://127.0.0.1:8000/admin

logue novamente.

Então acesse Licencas_Web e adicione a nova base.

Ao clicar em Nova base será necessário inserir:

Slug: nomedosave
cnpj: cnpjdaempresa
db name: savexml\*\*\*
db host: 64.181.163.190
db port: 5432
db user: postgres
db password: senha do postgres padrão da empresa
plano: qualquer um dos três

feito isto é necessário rodar o comando abaixo que irá criar as parametrizações iniciais e o usuario admin padrão:

Bash
python setup_mobile.py --tenant "nomedosaveinserido"

"Certifique-se de que o slug inserido no admin seja exatamente o mesmo nome usado no parâmetro --tenant."


Nota: As APIs podem ser validadas via Swagger em:

https://mobile-sps.site/api/schema/swagger-ui/


Para criar um app novo use o comando:

Bash
python manage.py startapp nomedodoapp

dessa forma cria os arquivos necessarios para o app de acordo com a estrtutura padrão do django.

Porém o projeto usa um padrão de arquitetura horizontal separado como no exemplo do app de pedidos, cada camada com sua responsabilidade:

para as versões Rest e web, quando formos criar api's usamos o padrão rest, quando formos criar django templates para versão web, usamos o padrão web.

📦 pedidos/
├── 📜 __init__.py
├── 📜 models.py          # Definição de tabelas e relações (ORM Django)
│
├── 📂 rest/              # Camada de API (Django Rest Framework)
│   ├── 📜 __init__.py
│   ├── 📜 serializers.py # Contratos DTO (Entrada/Saída de dados)
│   ├── 📜 urls.py        # Endpoints da API (ex: /api/pedidos/)
│   └── 📂 views/         # Lógica de controle da API
│       ├── 📜 listar.py
│       ├── 📜 criar.py
│       ├── 📜 atualizar.py
│       └── 📜 deletar.py
│
├── 📂 services/          # CAMADA CORE: Regras de negócio e integração
│   ├── 📜 __init__.py
│   └── 📜 logic.py       # Onde a "mágica" acontece e chama o SaveXML
│
└── 📂 web/               # Camada de Interface Web (Django Templates)
    ├── 📜 __init__.py
    ├── 📜 forms.py       # Validações e Contratos de formulários Web
    ├── 📜 urls.py        # Rotas das páginas HTML
    └── 📂 views/         # Controladores que renderizam os Templates
        ├── 📜 listar.py
        ├── 📜 criar.py
        └── ...


************\_\_\_************//---------------------------------//-------------------------------------//**************\_**************

Esses passos a seguir são feitos apenas pelo administrador do sistema.

2. Acesso ao Servidor (SSH)
   O acesso ao servidor Linux exige um par de chaves RSA.

Gerar chave localmente:

Bash
ssh-keygen -t rsa -P "" -f SPARTACUS.pem
Autorizar chave no servidor:
Copie o conteúdo de SPARTACUS.pem.pub e cole no servidor em: ~/.ssh/authorized_keys.

Conectar:

Bash
ssh -i SPARTACUS.pem ubuntu@168.75.73.117 3. Configuração do Ambiente de Produção
3.1 Gunicorn (Systemd)
O serviço do Gunicorn gerencia a aplicação Django.
Arquivo: /etc/systemd/system/gunicorn.service

Ini, TOML
[Unit]
Description=Gunicorn Django App
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/mobile-sps
ExecStart=/home/ubuntu/mobile-sps/venv/bin/gunicorn \
 --access-logfile - \
 --workers 9 \
 --threads 2 \
 --timeout 120 \
 --preload \
 --bind unix:127.0.0.1:8000 \
 core.wsgi:application

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
Comandos de Gerenciamento:

Bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo systemctl status gunicorn

# Logs do Gunicorn

sudo journalctl -u gunicorn
3.2 Nginx (Reverse Proxy)
Arquivo: /etc/nginx/sites-available/default

Nginx
server {
listen 80;
server_name 168.75.73.117;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

}
Validar e Reiniciar:

Bash
sudo nginx -t
sudo systemctl restart nginx 4. Manutenção e Logs
Atualização Manual no Servidor
Bash
cd /home/ubuntu/mobile-sps
source venv/bin/activate
git pull
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
sudo systemctl restart daphne
Monitoramento de Logs
Bash

# Logs de Erro Nginx

sudo tail -f /var/log/nginx/error.log

# Logs de Acesso Nginx

sudo tail -f /var/log/nginx/access.log 5. CI/CD: GitHub Actions (Blue/Green Deploy)
O projeto utiliza uma estratégia de Blue/Green Deploy. O script alterna o link simbólico (current) entre os diretórios blue e green para garantir zero downtime.

Principais etapas do Workflow:

Checkout & Cache: Baixa o código e faz cache das libs do Python.

Deploy via SSH:

Sincroniza o repositório (rsync).

Identifica qual ambiente (blue ou green) está inativo.

Roda as dependências e o collectstatic no ambiente alvo.

Health-check: Verifica se o novo ambiente responde com HTTP 200.

Swap: Se estiver OK, altera o symlink para o novo ambiente.

Notificação: Envia o status (Sucesso/Falha) para o bot do Telegram.
