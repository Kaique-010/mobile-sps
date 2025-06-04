-- Tabela de imagens antes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ordemservicoimgantes') THEN
        CREATE TABLE ordemservicoimgantes (
            iman_id SERIAL PRIMARY KEY,
            iman_empr INTEGER NOT NULL,
            iman_fili INTEGER NOT NULL,
            iman_orde INTEGER NOT NULL,
            iman_codi INTEGER NOT NULL,
            iman_come TEXT,
            iman_imag BYTEA,
            iman_obse VARCHAR(255),
            img_latitude DECIMAL(9,6),
            img_longitude DECIMAL(9,6),
            img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Índices para melhor performance
        CREATE INDEX idx_imgantes_ordem ON ordemservicoimgantes(iman_orde);
        CREATE INDEX idx_imgantes_empresa_filial ON ordemservicoimgantes(iman_empr, iman_fili);
        
        -- Constraint única para evitar duplicatas
        CREATE UNIQUE INDEX idx_imgantes_unique ON ordemservicoimgantes(iman_empr, iman_fili, iman_orde, iman_codi);
    END IF;
END
$$;

-- Tabela de imagens durante
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ordemservicoimgdurante') THEN
        CREATE TABLE ordemservicoimgdurante (
            imdu_id SERIAL PRIMARY KEY,
            imdu_empr INTEGER NOT NULL,
            imdu_fili INTEGER NOT NULL,
            imdu_orde INTEGER NOT NULL,
            imdu_codi INTEGER NOT NULL,
            imdu_come TEXT,
            imdu_imag BYTEA,
            imdu_obse VARCHAR(255),
            img_latitude DECIMAL(9,6),
            img_longitude DECIMAL(9,6),
            img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Índices para melhor performance
        CREATE INDEX idx_imgdurante_ordem ON ordemservicoimgdurante(imdu_orde);
        CREATE INDEX idx_imgdurante_empresa_filial ON ordemservicoimgdurante(imdu_empr, imdu_fili);
        
        -- Constraint única para evitar duplicatas
        CREATE UNIQUE INDEX idx_imgdurante_unique ON ordemservicoimgdurante(imdu_empr, imdu_fili, imdu_orde, imdu_codi);
    END IF;
END
$$;

-- Tabela de imagens depois
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ordemservicoimgdepois') THEN
        CREATE TABLE ordemservicoimgdepois (
            imde_id SERIAL PRIMARY KEY,
            imde_empr INTEGER NOT NULL,
            imde_fili INTEGER NOT NULL,
            imde_orde INTEGER NOT NULL,
            imde_codi INTEGER NOT NULL,
            imde_come TEXT,
            imde_imag BYTEA,
            imde_obse VARCHAR(255),
            img_latitude DECIMAL(9,6),
            img_longitude DECIMAL(9,6),
            img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Índices para melhor performance
        CREATE INDEX idx_imgdepois_ordem ON ordemservicoimgdepois(imde_orde);
        CREATE INDEX idx_imgdepois_empresa_filial ON ordemservicoimgdepois(imde_empr, imde_fili);
        
        -- Constraint única para evitar duplicatas
        CREATE UNIQUE INDEX idx_imgdepois_unique ON ordemservicoimgdepois(imde_empr, imde_fili, imde_orde, imde_codi);
    END IF;
END
$$;

-- Adicionar campos de GPS e data se não existirem nas tabelas existentes
DO $$
DECLARE
    v_table_names text[] := ARRAY['ordemservicoimgantes', 'ordemservicoimgdurante', 'ordemservicoimgdepois'];
    v_table_name text;
BEGIN
    FOREACH v_table_name IN ARRAY v_table_names
    LOOP
        -- Adicionar campo de latitude se não existir
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = v_table_name 
            AND column_name = 'img_latitude'
            AND table_schema = current_schema()
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN img_latitude DECIMAL(9,6)', v_table_name);
        END IF;

        -- Adicionar campo de longitude se não existir
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = v_table_name 
            AND column_name = 'img_longitude'
            AND table_schema = current_schema()
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN img_longitude DECIMAL(9,6)', v_table_name);
        END IF;

        -- Adicionar campo de data se não existir
        IF NOT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = v_table_name 
            AND column_name = 'img_data'
            AND table_schema = current_schema()
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN img_data TIMESTAMP DEFAULT CURRENT_TIMESTAMP', v_table_name);
        END IF;
    END LOOP;
END
$$; 