# mobile-sps

primeiramente é necessáro rodar o script de unicidade e criação da tabela de vinculo usuario empresa filial para o login

-- 1. Garante unicidade nas colunas referenciadas
ALTER TABLE uctabusers ADD CONSTRAINT uctabusers_uciduser_key UNIQUE (uciduser);
ALTER TABLE empresas ADD CONSTRAINT empresas_empr_codi_key UNIQUE (empr_codi);
ALTER TABLE filiais ADD CONSTRAINT filiais_empr_codi_key UNIQUE (empr_codi);

-- 2. Cria a tabela de vínculo
CREATE TABLE user_empresa_filial (
user_id INTEGER NOT NULL REFERENCES uctabusers(uciduser) ON DELETE CASCADE,
empresa_id INTEGER NOT NULL REFERENCES empresas(empr_codi) ON DELETE CASCADE,
filial_id INTEGER NOT NULL REFERENCES filiais(empr_codi) ON DELETE CASCADE
);

criamos o hash como o django pede para que possa ser possível o login
UPDATE uctabusers
SET
ucpassword = 'pbkdf2_sha256$1000000$SRty2PqvsjkcasowIEZsaB$85Duuvj2ZF7WBp83fqW9RMMcy/QGF6LYHDLqTG8Y6+g=',
ucusername = 'mobile',
uclogin = 'mobile'
WHERE uciduser = 150;

Libera as filiais para o acesso

    insert into user_empresa_filial (user_id, empresa_id, filial_id)
    values (150 , 1 , 1)


    insert into uctabusers (uciduser, ucusername, uclogin, ucpassword)
    values (150, 'mobile', 'mobile', 'pbkdf2_sha256$1000000$SRty2PqvsjkcasowIEZsaB$85Duuvj2ZF7WBp83fqW9RMMcy/QGF6LYHDLqTG8Y6+g=')

tabelas de listas_casamento v
CREATE TABLE lista_casamento (
list_empr INTEGER NOT NULL,
list_fili INTEGER NOT NULL,
list_nume BIGSERIAL PRIMARY KEY,
list_clie_id BIGINT NOT NULL,
list_data DATE NOT NULL,
list_stat CHAR(1) NOT NULL DEFAULT '0',
CONSTRAINT fk_lista_clie FOREIGN KEY (list_clie_id, list_empr)
REFERENCES entidades (enti_clie, enti_empr)
);

tabelas de iterns de lista de casamento
CREATE TABLE itens_lista_casamento (
id SERIAL PRIMARY KEY,
item_empr INTEGER,
item_fili INTEGER,
item_list BIGINT NOT NULL,
item_prod VARCHAR(50) NOT NULL,
item_comp VARCHAR(150),
CONSTRAINT fk_item_list FOREIGN KEY (item_list)
REFERENCES lista_casamento (list_nume) ON DELETE CASCADE,
CONSTRAINT fk_item_prod FOREIGN KEY (item_prod, item_empr)
REFERENCES produtos (prod_codi, prod_empr)
);

# Criar o usuario no shell

from Auth.models import Usuarios

usuario = Usuarios(
usua_codi=150,
usua_nome='admin'
)
usuario.set_password('roma3030@')
usuario.save()

print(usuario)
print(usuario.usua_codi)
print(usuario.password)

# Para acessar o shell e criar o usuario em outra base

from Auth.models import Usuarios

usuario = Usuarios.objects.using('default').create(
usua_codi=100,
usua_nome='leo'
)
usuario.set_password('roma3030@')
usuario.save(using='default')

-- Cria a sequence se não existir
CREATE SEQUENCE IF NOT EXISTS listacasamento_list_codi_seq;

-- Altera a coluna para usar a sequence como default
ALTER TABLE listacasamento
ALTER COLUMN list_codi SET DEFAULT nextval('listacasamento_list_codi_seq');

CREATE SEQUENCE item_item_seq
START WITH 1
INCREMENT BY 1
MINVALUE 1
MAXVALUE 9223372036854775807
CACHE 1;

ALTER TABLE itenslistacasamento
ALTER COLUMN item_item SET DEFAULT nextval('item_item_seq');

proximo nunero de itens manual

from django.db.models import Max
from listacasamento.models import ItensListaCasamento

def get_next_item_number(item_empr, item_fili, item_list):
from .models import ItensListaCasamento

        ultimo_item = (
            ItensListaCasamento.objects
            .filter(item_empr=item_empr, item_fili=item_fili, item_list=item_list)
            .order_by('-item_item')
            .first()
        )
        return (ultimo_item.item_item + 1) if ultimo_item else 1

as alterações como update, e create passmaos na viewset alterando os moeels do django
