from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Renegociacao", "0004_safe_add_rene_stat_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE IF EXISTS renegociado
            ALTER COLUMN rene_titu TYPE VARCHAR(255);
            """,
            reverse_sql="",
        ),
    ]
