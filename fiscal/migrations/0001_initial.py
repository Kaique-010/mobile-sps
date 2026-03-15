from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NFeDocumento",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("empresa", models.IntegerField(db_index=True)),
                ("filial", models.IntegerField(db_index=True)),
                ("chave", models.CharField(db_index=True, max_length=44)),
                ("tipo", models.CharField(choices=[("entrada", "Entrada"), ("saida", "Saída")], max_length=10)),
                ("xml_original", models.TextField()),
                ("json_normalizado", models.TextField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "fiscal_nfe_documento",
                "unique_together": {("empresa", "filial", "chave")},
                "indexes": [
                    models.Index(fields=["empresa", "filial", "tipo"], name="fiscal_nfe_empresa_04e07a_idx"),
                    models.Index(fields=["empresa", "filial", "criado_em"], name="fiscal_nfe_empresa_5c2f2c_idx"),
                ],
            },
        ),
    ]
