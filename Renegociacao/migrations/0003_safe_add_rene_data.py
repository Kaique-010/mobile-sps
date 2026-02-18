from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("Renegociacao", "0002_safe_add_columns"),
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE IF EXISTS renegociado
                ADD COLUMN IF NOT EXISTS rene_data DATE;
            """,
            reverse_sql="""
            """,
        ),
    ]
