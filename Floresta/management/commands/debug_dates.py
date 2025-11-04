from django.core.management.base import BaseCommand
from Floresta.models import Osflorestal
from django.conf import settings
from core.utils import get_db_from_slug

class Command(BaseCommand):
    help = 'Debug problematic dates in Osflorestal'

    def handle(self, *args, **options):
        self.stdout.write("=== DEBUG FLORESTA DATES ===")
        
        # Tentar configurar conexão casaa
        try:
            db_alias = get_db_from_slug('casaa')
            self.stdout.write(f"Using database: {db_alias}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not configure casaa db: {e}"))
            db_alias = 'default'
            self.stdout.write("Using default database")
        
        try:
            # Buscar registros sem filtro
            records = Osflorestal.objects.using(db_alias).all()[:10]
            records_list = list(records)
            self.stdout.write(f"Found {len(records_list)} records")
            
            for i, record in enumerate(records_list):
                self.stdout.write(f"\n--- Record {i+1} ---")
                self.stdout.write(f"ID: {record.osfl_empr}-{record.osfl_fili}-{record.osfl_orde}")
                
                # Check osfl_data_aber
                try:
                    data_aber = record.osfl_data_aber
                    self.stdout.write(f"osfl_data_aber: {data_aber} (type: {type(data_aber)})")
                    if data_aber:
                        try:
                            year = data_aber.year
                            self.stdout.write(f"Year: {year}")
                            if year < 1900 or year > 2100:
                                self.stdout.write(self.style.WARNING(f"INVALID YEAR: {year}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error accessing year: {e}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error accessing osfl_data_aber: {e}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"General error: {e}"))
            import traceback
            traceback.print_exc()