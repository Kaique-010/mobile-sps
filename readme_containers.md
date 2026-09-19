README — Containers PostgreSQL / SaveWeb
1. Servidor atual

Os containers PostgreSQL do ambiente SaveWeb estão hospedados no novo servidor Oracle Cloud:

IP: 168.75.73.117
Usuário SSH: ubuntu
PostgreSQL: 16
Porta PostgreSQL: 5432


2. Listar os containers
Containers em execução
docker ps
Todos os containers
docker ps -a
Ver os logs de um container
docker logs -f <container_id>
3. Containers do ambiente

Atualmente existem três containers principais:

sps_web
saas_postgres
pg_backup
Ver os containers
docker ps -a
Ver logs do PostgreSQL
docker logs -f sps_web
docker logs -f saas_postgres
Ver logs do backup
docker logs -f pg_backup
4. Bancos disponíveis

Os bancos migrados para o novo servidor incluem:

base_modelo
cliente_teste
postgres

saveweb001
saveweb002
saveweb003
saveweb004
saveweb005
saveweb006
saveweb007
saveweb008

Para listar os bancos:

docker exec sps_web psql -U postgres -c "\l"
5. Verificar os arquivos de backup

Os backups são armazenados no host em:

/home/ubuntu/pg_backups/

Para visualizar:

ls -lh /home/ubuntu/pg_backups/

Ou diretamente pelo container:

docker exec pg_backup ls -lh /backups/

Para visualizar os backups de um banco específico:

docker exec pg_backup ls -lh /backups/saveweb001/
docker exec pg_backup ls -lh /backups/saveweb008/

Para o banco postgres:

docker exec pg_backup ls -lh /backups/postgres/
6. Logs do processo de backup
Últimas 50 linhas
docker logs --tail 50 pg_backup
Acompanhar os logs em tempo real
docker logs -f pg_backup
7. Ver o script de backup

Para visualizar o script que está sendo executado:

docker exec pg_backup cat /backup.sh

Para localizar scripts .sh dentro do container:

docker exec pg_backup find / -name "*.sh" 2>/dev/null
8. Ver o processo executado dentro do container
docker exec pg_backup ps aux
9. Ver as variáveis de ambiente
docker inspect pg_backup | grep -A 20 '"Env"'

As credenciais do PostgreSQL são carregadas através do arquivo:

/home/ubuntu/pg_backup.env
10. Configuração automática dos backups

O container pg_backup executa automaticamente o processo de backup.

Frequência
A cada 24 horas

O intervalo utilizado pelo script é:

sleep 86400
Bancos

O script identifica automaticamente os bancos PostgreSQL que não são templates:

SELECT datname
FROM pg_database
WHERE datistemplate = false;

Portanto, novos bancos criados no PostgreSQL também passam a ser considerados automaticamente pelo processo de backup.

11. Retenção dos backups

Os arquivos possuem retenção de 7 dias.

O comando responsável pela limpeza é:

find /backups -type f -mtime +7 -delete

Arquivos com mais de 7 dias são removidos automaticamente.

12. Localização dos backups

No host Oracle:

/home/ubuntu/pg_backups/

Dentro do container:

/backups/

O diretório é montado através de:

-v /home/ubuntu/pg_backups:/backups
13. Atualização do base_modelo

A cada ciclo de backup, o base_modelo é recriado utilizando somente a estrutura mais recente do saveweb001.

Fluxo:

saveweb001
    │
    │ pg_dump -s
    ▼
base_modelo.sql
    │
    ▼
DROP DATABASE base_modelo
    │
    ▼
CREATE DATABASE base_modelo
    │
    ▼
Restauração da estrutura
    │
    ▼
base_modelo atualizado

Comando utilizado para gerar somente a estrutura:

pg_dump -h saas_postgres -U postgres -s saveweb001 > /tmp/base_modelo.sql

O objetivo é manter:

base_modelo = estrutura mais recente do saveweb001

O base_modelo não contém os dados do saveweb001, somente sua estrutura.

14. Recriar o container pg_backup

Caso seja necessário recriar o container:

docker stop pg_backup
docker rm pg_backup

Depois:

docker run -d \
  --name pg_backup \
  --env-file /home/ubuntu/pg_backup.env \
  --network sps_network \
  -v /home/ubuntu/pg_backups:/backups \
  postgres:16 \
  bash -c "
while true; do

echo 'Iniciando ciclo de backup...';

DATABASES=\$(psql -h saas_postgres -U postgres -d postgres -t -c \"SELECT datname FROM pg_database WHERE datistemplate = false;\");

for DB in \$DATABASES; do

  echo \"Backup do banco: \$DB\";

  mkdir -p /backups/\$DB;

  pg_dump -h saas_postgres -U postgres -F c -b \$DB | gzip > /backups/\$DB/\${DB}_\$(date +%Y%m%d_%H%M).dump.gz;

done;

find /backups -type f -mtime +7 -delete;

echo 'Ciclo finalizado.';

echo 'Atualizando base_modelo...';

pg_dump -h saas_postgres -U postgres -s saveweb001 > /tmp/base_modelo.sql;

psql -h saas_postgres -U postgres -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'base_modelo';\";

psql -h saas_postgres -U postgres -d postgres -c \"DROP DATABASE IF EXISTS base_modelo;\";

psql -h saas_postgres -U postgres -d postgres -c \"CREATE DATABASE base_modelo;\";

psql -h saas_postgres -U postgres -d base_modelo < /tmp/base_modelo.sql;

rm /tmp/base_modelo.sql;

echo 'base_modelo atualizado com sucesso!';

sleep 86400;

done"

Importante: no novo ambiente o script utiliza saas_postgres em vez do antigo IP Docker 172.17.0.2. Isso evita depender de um IP interno fixo do container.

15. Rede Docker

Os containers PostgreSQL e backup estão conectados à rede:

sps_network

Verificar:

docker network inspect sps_network

Containers conectados:

sps_web
saas_postgres
pg_backup

O pg_backup consegue acessar o PostgreSQL através do nome:

saas_postgres

em vez de utilizar diretamente o IP interno do Docker.



-----------------//----------------------------------------------------------------------------

16. Acesso ao servidor via SSH

No Windows, utilizar a chave:

C:\Users\"leoka"\SPARTACUS.pem

Comando:

ssh -i "C:\Users\leoka\SPARTACUS.pem" ubuntu@168.75.73.117

Depois de conectado:

docker ps

Para verificar os backups:

ls -lh /home/ubuntu/pg_backups/
17. Acesso pelo pgAdmin

O PostgreSQL está disponível externamente pela porta:

5432
Configuração no pgAdmin

Acesse:

Servers
→ Register
→ Server
General

Name:

PostgreSQL - SaveWeb Novo
Connection
Campo	Valor
Host name/address	168.75.73.117
Port	5432
Maintenance database	postgres
Username	postgres
Password	senha do PostgreSQL
SSL mode	conforme configuração atual, normalmente Prefer

Depois clique em:

Save

O pgAdmin deverá apresentar os bancos:

Databases
├── base_modelo
├── cliente_teste
├── postgres
├── saveweb001
├── saveweb002
├── saveweb003
├── saveweb004
├── saveweb005
├── saveweb006
├── saveweb007
└── saveweb008

Não é necessário criar uma conexão separada para cada savewebXXX. Uma única conexão com 168.75.73.117:5432 permite acompanhar todos os bancos aos quais o usuário PostgreSQL possui acesso.

18. Resumo da infraestrutura
                         ORACLE CLOUD
                       168.75.73.117
                              │
                     PostgreSQL :5432
                              │
                ┌─────────────┴─────────────┐
                │                           │
             sps_web                  saas_postgres
                │                           │
                └────────── pgdata ─────────┘
                              │
                         pg_backup
                              │
                    /home/ubuntu/pg_backups
                              │
                    ┌─────────┴─────────┐
                    │                   │
               Backups .dump.gz    base_modelo
                    │                   │
              retenção 7 dias    estrutura do
                                 saveweb001
Endereços importantes
Servidor novo:
168.75.73.117

PostgreSQL:
168.75.73.117:5432

SSH:
ubuntu@168.75.73.117

Backups:
 /home/ubuntu/pg_backups/

Rede Docker:
sps_network

PostgreSQL para o pg_backup:
saas_postgres
Regra principal
save1 / licencas_web
        │
        │ identifica o banco e servidor
        ▼
savewebXXX
        │
        ▼
168.75.73.117:5432