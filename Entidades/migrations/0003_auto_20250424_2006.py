# Generated by Django 2.2.28 on 2025-04-24 23:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Entidades', '0002_auto_20250424_1005'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sequencial',
            name='id',
        ),
        migrations.AlterField(
            model_name='sequencial',
            name='nome_sequencial',
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
    ]
