# Generated by Django 2.2.28 on 2025-07-09 08:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ComissaoSps',
            fields=[
                ('comi_id', models.AutoField(primary_key=True, serialize=False)),
                ('comi_empr', models.IntegerField()),
                ('comi_fili', models.IntegerField()),
                ('comi_func', models.CharField(max_length=255)),
                ('comi_func_nome', models.CharField(blank=True, max_length=100, null=True)),
                ('comi_clie', models.CharField(max_length=255)),
                ('comi_clie_nome', models.CharField(blank=True, max_length=100, null=True)),
                ('comi_cate', models.CharField(choices=[('1', 'Melhoria'), ('2', 'Implantação'), ('3', 'Dashboards'), ('4', 'Mobile'), ('5', 'Vendas')], max_length=50)),
                ('comi_valo_tota', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comi_impo', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comi_valo_liqu', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comi_perc', models.DecimalField(decimal_places=2, max_digits=5)),
                ('comi_comi_tota', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comi_parc', models.IntegerField()),
                ('comi_comi_parc', models.DecimalField(decimal_places=2, max_digits=12)),
                ('comi_form_paga', models.CharField(max_length=20)),
                ('comi_data_entr', models.DateField()),
            ],
            options={
                'db_table': 'comissoes_sps',
                'managed': False,
            },
        ),
    ]
