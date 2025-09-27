from django.core.management.base import BaseCommand
from core.models import Profession

class Command(BaseCommand):
    help = "Precarica solo le professioni nel database"

    def handle(self, *args, **options):
        professions = ['Ufficio',
                  'Ufficio - Preposto',
                  'Magazzino',
                  'Coordinatore Generale - Preposto',
                  'Coordinatore Operativo COVA - Preposto',
                  'Tecnico Specializzato CNP/Gas Free - Preposto solo WE',
                  'Tecnico Specializzato CNP/Gas Free - Preposto',
                  'Front Office BO 1 - Preposto',
                  'Front Office BO2',
                  'Operatore analisi Gas (Linee e Claus) - Preposto',
                  'Operatore analisi Gas (Linee e Claus)',
                  'Capo Squadra - Preposto',
                  'Soccorritore',
                  'Supervisore Ponteggi Senior - Preposto',
                  'Supervisore Ponteggi Junior',
                  'Supervisore Senior - Preposto',
                  'Operatore Addetto Front Office Aree Pozzo',
                  'Training',
                  'Delegato ai Lavori - Preposto',
                  'Supervisore Area MISE - Preposto',
                  'Supervisore Senior - KPI',
                  'Supervisore Senior',
                  'Supervisore Senior Posti Afferenti - Preposto',
                  'Supervisore Junior - Posti Afferenti',
                  'Supervisore Junior - (principalmente LOTO/ACAM, a discrezione del coordinatore)',
                  'Supervisore Junior - (principalmente GST, a discrezione del coordinatore)',
                  'Supervisore Junior - Verifica attrezzatture/Gestione Magazzino HSE',
                  'Ispettore Ponteggi - Preposto',
                  'Operatore Addetto Controllo Mezzi - IDL - Preposto',
                  'Operatore Addetto Controllo Mezzi - IDL',
                  'ICT - Preposto (orario 07:00-19:00)',
                  'ICT - Preposto (orario 19:00-07:00)',
                  'RDC  - Preposto',
                  'Coordinatore Operativo Altri Siti DIME (ad eccezione del COVA) - Preposto',
                  'Supervisore Senior Pisticci',
                  'Supervisore Senior Candela',
                  'Supervisore Senior Roseto',
                  'Delegato ai Lavori - Centrali Minori (DEG 5) - Preposto',
                  'Delegato ai Lavori - Centrali Minori  (Torrente Vulgano 9 ) - Preposto',
                  'Supervisione HSE Perforzione/Workover  - CF 3 Day - Orario 07:00-19:00',
                  'Supervisione HSE Perforzione/Workover  - CF 3 Night - Orario 19:00_07:00',
                  'Supervisione HSE Perforzione/Workover  - Alli 4 Day - Orario 07:00-19:00',
                  'Supervisione HSE Perforzione/Workover  - CM 2 - Orario 07:00-19:00',
                  'Supervisione HSE Perforzione/Workover  - Volturino 1 - Orario 07:00-19:00',
                  'ME1: WI tests',
                  'Jolly - RDC',
                  'Jolly - a discezione del Coordinatore Operativo COVA',
                  'Jolly - a discezione del Coordinatore Operativo DIME (priorità comparto Delegati)'
                  ]

        for name in professions:
            obj, created = Profession.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Aggiunta professione: {name}"))
            else:
                self.stdout.write(f"Già presente: {name}")
