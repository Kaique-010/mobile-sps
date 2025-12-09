from django.db import migrations


def load_licencas_from_json(apps, schema_editor):
    LicencaWeb = apps.get_model('licencas_web', 'LicencaWeb')

    try:
        import json
        from pathlib import Path
        from decouple import config

        json_path = Path(__file__).resolve().parents[2] / 'core' / 'licencas.json'
        if not json_path.exists():
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data:
            slug = entry.get('slug')
            if not slug:
                continue

            prefix = slug.upper()
            db_user = config(f'{prefix}_DB_USER', default='')
            db_password = config(f'{prefix}_DB_PASSWORD', default='')

            import json as _json
            LicencaWeb.objects.update_or_create(
                slug=slug,
                defaults={
                    'cnpj': entry.get('cnpj', ''),
                    'db_name': entry.get('db_name', ''),
                    'db_host': entry.get('db_host', ''),
                    'db_port': entry.get('db_port', ''),
                    'modulos': _json.dumps(entry.get('modulos', []) or []),
                    'db_user': db_user,
                    'db_password': db_password,
                },
            )
    except Exception:
        # Silencioso: retrocompatibilidade se não conseguir carregar
        pass


def reverse_func(apps, schema_editor):
    # Nenhuma ação de reverse de dados
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('licencas_web', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_licencas_from_json, reverse_func),
    ]
