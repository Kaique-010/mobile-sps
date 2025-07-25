# Generated by Django 2.2.28 on 2025-07-09 08:33

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ordemprodetapa',
            fields=[
                ('opet_orpr', models.IntegerField(primary_key=True, serialize=False)),
                ('opet_codi', models.IntegerField()),
                ('opet_desc', models.CharField(blank=True, max_length=1000, null=True)),
                ('opet_func', models.IntegerField(blank=True, null=True)),
                ('opet_dati', models.DateField(blank=True, null=True)),
                ('opet_datf', models.DateField(blank=True, null=True)),
                ('opet_equi', models.IntegerField(blank=True, null=True)),
                ('opet_etap', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ordemprodetapa',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Ordemprodfotos',
            fields=[
                ('orpr_codi', models.IntegerField(primary_key=True, serialize=False)),
                ('orpr_empr', models.IntegerField()),
                ('orpr_fili', models.IntegerField()),
                ('orpr_nume_foto', models.IntegerField()),
                ('orpr_desc_foto', models.TextField(blank=True, null=True)),
                ('orpr_foto_ante', models.BinaryField(blank=True, null=True)),
                ('orpr_foto_atua', models.BinaryField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ordemprodfotos',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Ordemproditens',
            fields=[
                ('orpr_codi', models.IntegerField(primary_key=True, serialize=False)),
                ('orpr_empr', models.IntegerField()),
                ('orpr_fili', models.IntegerField()),
                ('orpr_pedi', models.IntegerField()),
                ('orpr_item', models.IntegerField()),
                ('orpr_prod', models.CharField(blank=True, max_length=20, null=True)),
            ],
            options={
                'db_table': 'ordemproditens',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Ordemprodmate',
            fields=[
                ('orpm_orpr', models.IntegerField(primary_key=True, serialize=False)),
                ('orpm_codi', models.IntegerField()),
                ('orpm_prod', models.CharField(blank=True, max_length=20, null=True)),
                ('orpm_quan', models.DecimalField(blank=True, decimal_places=5, max_digits=15, null=True)),
                ('orpm_unit', models.DecimalField(blank=True, decimal_places=5, max_digits=15, null=True)),
                ('orpm_tota', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_med1', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_med2', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_med3', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_qdme', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_qdmt', models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ('orpm_cust', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_lkst', models.CharField(blank=True, max_length=6, null=True)),
                ('orpm_esto', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpm_totv', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
            ],
            options={
                'db_table': 'ordemprodmate',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Ordemproducao',
            fields=[
                ('orpr_codi', models.AutoField(primary_key=True, serialize=False)),
                ('orpr_entr', models.DateTimeField()),
                ('orpr_fech', models.DateTimeField(blank=True, null=True)),
                ('orpr_daen', models.DateTimeField(blank=True, null=True)),
                ('orpr_nuca', models.CharField(max_length=6, unique=True)),
                ('orpr_clie', models.IntegerField()),
                ('orpr_valo', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('orpr_prev', models.DateTimeField()),
                ('orpr_empr', models.IntegerField(db_column='orpr_empr', default=1)),
                ('orpr_fili', models.IntegerField(default=1)),
                ('orpr_tipo', models.CharField(choices=[('1', 'Confecção'), ('2', 'Conserto'), ('3', 'Orçamento'), ('4', 'Conserto Relógio')], default='Confecção', max_length=100)),
                ('orpr_gara', models.BooleanField()),
                ('orpr_vend', models.IntegerField()),
                ('orpr_desc', models.TextField(blank=True, null=True)),
                ('orpr_stat', models.IntegerField(default=1)),
                ('orpr_prod', models.CharField(blank=True, max_length=20, null=True)),
                ('orpr_quan', models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ('orpr_gram_clie', models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ('orpr_cort', models.BooleanField()),
            ],
            options={
                'db_table': 'ordemproducao',
            },
        ),
    ]
