from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Renegociacao", "0003_safe_add_rene_data"),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE IF EXISTS renegociado
                ADD COLUMN IF NOT EXISTS rene_stat VARCHAR(1),
                ADD COLUMN IF NOT EXISTS rene_usua INTEGER,
                ADD COLUMN IF NOT EXISTS rene_obse VARCHAR(250),
                ADD COLUMN IF NOT EXISTS rene_perc_mult NUMERIC(5,2),
                ADD COLUMN IF NOT EXISTS rene_valo_mult NUMERIC(15,2),
                ADD COLUMN IF NOT EXISTS rene_perc_juro NUMERIC(6,3),
                ADD COLUMN IF NOT EXISTS rene_valo_juro NUMERIC(15,2),
                ADD COLUMN IF NOT EXISTS rene_juro_dia BOOLEAN,
                ADD COLUMN IF NOT EXISTS rene_dias INTEGER;
            """,
            reverse_sql="""
            """,
        ),
        migrations.RunSQL(
            """
            UPDATE renegociado SET rene_stat = 'A' WHERE rene_stat IS NULL;
            """,
            reverse_sql="",
        ),
    ]
