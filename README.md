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
