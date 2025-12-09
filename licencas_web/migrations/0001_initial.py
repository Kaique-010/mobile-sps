from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LicencaWeb',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=64, unique=True)),
                ('cnpj', models.CharField(max_length=20)),
                ('db_name', models.CharField(max_length=100)),
                ('db_host', models.CharField(max_length=200)),
                ('db_port', models.CharField(max_length=10)),
                ('modulos', models.TextField(default='[]', blank=True)),
                ('db_user', models.CharField(max_length=128, blank=True, default='')),
                ('db_password', models.CharField(max_length=256, blank=True, default='')),
            ],
            options={
                'verbose_name': 'Licença Web',
                'verbose_name_plural': 'Licenças Web',
            },
        ),
    ]
