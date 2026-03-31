PARA LISTAR OS CONTAINERS:

docker ps -

verificar os containers em execução:

docker ps -a

verificar o conteudo dos containers:

docker logs -f <container_id>

# Ver se os arquivos de backup estão sendo gerados

docker exec pg_backup ls -lh /backups/

ubuntu@Instncia-Sps-Training:~$ docker exec pg_backup ls -lh /backups/
total 20K
drwxr-xr-x 2 root root 4.0K Mar 31 11:29 cliente_teste
drwxr-xr-x 2 root root 4.0K Mar 31 11:29 postgres
drwxr-xr-x 2 root root 4.0K Mar 31 11:29 saveweb001
drwxr-xr-x 2 root root 4.0K Mar 31 11:29 saveweb002
drwxr-xr-x 2 root root 4.0K Mar 31 11:29 saveweb003
ubuntu@Instncia-Sps-Training:~$

# Ver os logs com mais detalhes (últimas 50 linhas)

docker logs --tail 50 pg_backup

# Ver o script de backup que está sendo executado

docker exec pg_backup cat /backup.sh

# Ver o conteúdo dentro de cada pasta

docker exec pg_backup ls -lh /backups/saveweb001/
docker exec pg_backup ls -lh /backups/postgres/

# Achar o script

docker exec pg_backup find / -name "\*.sh" 2>/dev/null

# Ver o que está rodando dentro do container

docker exec pg_backup ps aux

# Ver as variáveis de ambiente (pode ter pistas da config)

docker inspect pg_backup | grep -A 20 '"Env"'

Backup rodando todo dia às 11:29 automaticamente
5 bancos sendo salvos: postgres, cliente_teste, saveweb001, saveweb002, saveweb003
7 dias de retenção automática (arquivos mais antigos são deletados sozinhos)
Arquivos salvos em /home/ubuntu/pg_backups/ no host

deixar sempre o base modelo com a estrtutura padrão do saveweb001 que é sempre o mais recente

docker stop pg_backup
docker rm pg_backup

docker run -d \
 --name pg_backup \
 --env-file /home/ubuntu/pg_backup.env \
 -v /home/ubuntu/pg_backups:/backups \
 postgres:16 \
 bash -c "
while true; do
echo 'Iniciando ciclo de backup...';

    DATABASES=\$(psql -h 172.17.0.2 -U postgres -d postgres -t -c \"SELECT datname FROM pg_database WHERE datistemplate = false;\");

    for DB in \$DATABASES; do
      echo \"Backup do banco: \$DB\";
      mkdir -p /backups/\$DB;
      pg_dump -h 172.17.0.2 -U postgres -F c -b \$DB | gzip > /backups/\$DB/\${DB}_\$(date +%Y%m%d_%H%M).dump.gz;
    done;

    find /backups -type f -mtime +7 -delete;

    echo 'Ciclo finalizado.';

    echo 'Atualizando base_modelo...';

    # Dump só estrutura do saveweb001
    pg_dump -h 172.17.0.2 -U postgres -s saveweb001 > /tmp/base_modelo.sql;

    # Dropa e recria o base_modelo
    psql -h 172.17.0.2 -U postgres -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'base_modelo';\";
    psql -h 172.17.0.2 -U postgres -d postgres -c \"DROP DATABASE IF EXISTS base_modelo;\";
    psql -h 172.17.0.2 -U postgres -d postgres -c \"CREATE DATABASE base_modelo;\";

    # Restaura a estrutura
    psql -h 172.17.0.2 -U postgres -d base_modelo < /tmp/base_modelo.sql;

    rm /tmp/base_modelo.sql;

    echo 'base_modelo atualizado com sucesso!';

    sleep 86400;

done"
