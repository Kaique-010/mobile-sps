from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("formulacao", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="formulaitem",
            name="form_baixa_estoque",
            field=models.BooleanField(default=True),
        ),
    ]

