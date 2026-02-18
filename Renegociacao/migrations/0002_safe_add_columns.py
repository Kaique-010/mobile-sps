from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Renegociacao", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE IF EXISTS renegociado
                ADD COLUMN IF NOT EXISTS rene_vlfn NUMERIC(15,2),
                ADD COLUMN IF NOT EXISTS rene_desc NUMERIC(15,2),
                ADD COLUMN IF NOT EXISTS rene_pai INTEGER;
            """,
            reverse_sql="""
            -- reverso intencionalmente vazio
            """,
        ),
        migrations.RunSQL(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_name = 'renegociado'
                      AND tc.constraint_type = 'FOREIGN KEY'
                      AND tc.constraint_name = 'renegociado_rene_pai_fk'
                ) THEN
                    ALTER TABLE renegociado
                    ADD CONSTRAINT renegociado_rene_pai_fk
                    FOREIGN KEY (rene_pai) REFERENCES renegociado(rene_id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_name = 'renegociado'
                      AND tc.constraint_name = 'renegociado_rene_pai_fk'
                ) THEN
                    ALTER TABLE renegociado
                    DROP CONSTRAINT renegociado_rene_pai_fk;
                END IF;
            END $$;
            """,
        ),
    ]
