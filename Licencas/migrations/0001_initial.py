# Generated by Django 2.2.28 on 2025-07-09 08:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Empresas',
            fields=[
                ('empr_codi', models.AutoField(db_column='empr_codi', primary_key=True, serialize=False)),
                ('empr_nome', models.CharField(db_column='empr_nome', max_length=100, verbose_name='Nome da Empresa')),
                ('empr_docu', models.CharField(db_column='empr_cnpj', max_length=14, unique=True, verbose_name='CNPJ')),
            ],
            options={
                'db_table': 'empresas',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Filiais',
            fields=[
                ('empr_empr', models.IntegerField(db_column='empr_empr', primary_key=True, serialize=False)),
                ('empr_nome', models.CharField(db_column='empr_nome', max_length=100, verbose_name='Nome da Filial')),
                ('empr_docu', models.CharField(db_column='empr_cnpj', max_length=14, unique=True, verbose_name='CNPJ da Filial')),
            ],
            options={
                'db_table': 'filiais',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Licencas',
            fields=[
                ('lice_id', models.AutoField(primary_key=True, serialize=False)),
                ('lice_docu', models.CharField(max_length=14, unique=True)),
                ('lice_nome', models.CharField(max_length=100)),
                ('lice_emai', models.EmailField(blank=True, max_length=254, null=True)),
                ('lice_bloq', models.BooleanField(default=False)),
                ('lice_nume_empr', models.IntegerField()),
                ('lice_nume_fili', models.IntegerField()),
                ('_log_data', models.DateField(blank=True, null=True)),
                ('_log_time', models.TimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'licencas',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Usuarios',
            fields=[
                ('usua_codi', models.AutoField(primary_key=True, serialize=False)),
                ('usua_nome', models.CharField(max_length=150, unique=True)),
                ('password', models.CharField(db_column='usua_senh_mobi', max_length=128)),
                ('usua_seto', models.IntegerField(db_column='usua_seto')),
            ],
            options={
                'db_table': 'usuarios',
                'managed': False,
            },
        ),
    ]
