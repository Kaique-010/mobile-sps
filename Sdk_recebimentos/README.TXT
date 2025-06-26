TABELAS

CREATE TABLE recebimentosdk (
    sdk_id SERIAL PRIMARY KEY,
    sdk_empr INTEGER DEFAULT 1 NOT NULL,
    sdk_fili INTEGER DEFAULT 1 NOT NULL,
    sdk_pedi INTEGER NOT NULL,
    sdk_tipo VARCHAR(10) CHECK (sdk_tipo IN ('pix', 'debito', 'credito')),
    sdk_valo NUMERIC(10, 2) NOT NULL,
    sdk_parc INTEGER DEFAULT 1 NOT NULL,
    sdk_stat VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    sdk_seri VARCHAR(20) DEFAULT 'SDK' NOT NULL,
    sdk_data TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    sdk_resp VARCHAR(255),
    sdk_erro VARCHAR(255),
    CONSTRAINT recebimentosdk_unique UNIQUE (sdk_empr, sdk_fili, sdk_pedi)
);



CREATE TABLE "TituloReceberSdk" (
    titu_id SERIAL PRIMARY KEY,
    titu_empr INTEGER DEFAULT 1 NOT NULL,
    titu_fili INTEGER DEFAULT 1 NOT NULL,
    titu_rece INTEGER NOT NULL REFERENCES recebimentosdk(sdk_id) ON DELETE CASCADE,
    titu_nume INTEGER NOT NULL,
    titu_valo NUMERIC(10, 2) NOT NULL,
    titu_seri VARCHAR(20) DEFAULT 'SDK' NOT NULL,
    titu_data DATE NOT NULL,
    titu_stat VARCHAR(20) DEFAULT 'previsto' NOT NULL,
    CONSTRAINT titulorecebersdk_unique UNIQUE (titu_empr, titu_fili, titu_rece, titu_nume)
);

