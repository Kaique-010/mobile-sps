from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("GestaoObras", "0002_auto_20260330_1643"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="obramaterialestoquesaldo",
            options={"ordering": ("-omes_data_movi", "-id")},
        ),
        migrations.AlterUniqueTogether(
            name="obramaterialestoquesaldo",
            unique_together=set(),
        ),
    ]

