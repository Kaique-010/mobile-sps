TABELAS

CREATE TABLE "recebimentosdk" (
    "id" serial NOT NULL PRIMARY KEY,
    "sdk_pedi" varchar(20) NOT NULL,
    "sdk_tipo" varchar(10) NOT NULL,
    "sdk_valo" numeric(12, 2) NOT NULL,
    "sdk_parc" integer NOT NULL,
    "sdk_stat" varchar(10) NOT NULL
);


CREATE TABLE "titulorecebersdk" (
    "id" serial NOT NULL PRIMARY KEY,
    "tit_pedi" varchar(20) NOT NULL,
    "tit_forma" varchar(10) NOT NULL,
    "tit_valor" numeric(12, 2) NOT NULL,
    "tit_parcela" varchar(5) NOT NULL,
    "tit_venc" date NOT NULL,
    "tit_stat" varchar(10) NOT NULL
);
