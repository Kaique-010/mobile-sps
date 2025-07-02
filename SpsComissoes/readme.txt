    CREATE TABLE comissoes_sps (
        comi_id SERIAL PRIMARY KEY,
        comi_empr INT,
        comi_fili INT,
        comi_func INT, 
        comi_clie INT,
        comi_cate VARCHAR(2),
        comi_valo_tota NUMERIC(12,2),
        comi_impo NUMERIC(12,2),
        comi_valo_liqu NUMERIC(12,2),
        comi_perc NUMERIC(5,2),
        comi_comi_tota NUMERIC(12,2),
        comi_parc INT,
        comi_comi_parc NUMERIC(12,2),
        comi_form_paga VARCHAR(20),
        comi_data_entr DATE
    );
