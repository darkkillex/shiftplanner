from django.core.management.base import BaseCommand
from core.models import Company, Profession, Employee, ShiftType, Plan
from django.contrib.auth import get_user_model
from datetime import time
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed demo data"

    def handle(self, *args, **opts):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Superuser admin/admin created.'))

        c, _ = Company.objects.get_or_create(name='RINA Consulting S.p.A.')
        for p in ['Ufficio',
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
                  ]:
            Profession.objects.get_or_create(name=p)

        employees = [
            ('Nicola', 'Mastrangelo', 'ACM001', 'nicola.mastrangelo@rina.org'),
            ('Rocco', 'Lentisco', 'ACM002', 'rocco.lentisco@rina.org'),
            ('Antonio', 'Grosso', 'ACM003', 'antonio.grosso@rina.org'),
            ('Vincenzo', 'Piscione', 'ACM004', 'vincenzo.piscione@rina.org'),
        ]
        for fn, ln, mat, em in employees:
            Employee.objects.get_or_create(first_name=fn, last_name=ln, matricola=mat, email=em,
                                           defaults={'company': c})

        ShiftType.objects.get_or_create(code='A - 4/2', defaults={'label': 'Turno A - 4/2', 'start_time': time(6, 0),
                                                                  'end_time': time(14, 0)})
        ShiftType.objects.get_or_create(code='B - 4/2', defaults={'label': 'Turno B - 4/2', 'start_time': time(14, 0),
                                                                  'end_time': time(22, 0)})
        ShiftType.objects.get_or_create(code='C - 4/2', defaults={'label': 'Turno C- 4/2', 'start_time': time(22, 0),
                                                                  'end_time': time(6, 0)})
        ShiftType.objects.get_or_create(code='D - 5/2', defaults={'label': 'Turno D- 5/2', 'start_time': time(8, 0),
                                                                  'end_time': time(17, 0)})
        ShiftType.objects.get_or_create(code='12H - D - 7/7',
                                        defaults={'label': 'Turno 12H - Giorno - 7/7', 'start_time': time(7, 0),
                                                  'end_time': time(19, 0)})
        ShiftType.objects.get_or_create(code='12H - N - 7/7',
                                        defaults={'label': 'Turno 12H - Notte - 7/7', 'start_time': time(19, 0),
                                                  'end_time': time(7, 0)})

        now = timezone.localdate()
        admin = User.objects.get(username='admin')
        Plan.objects.get_or_create(month=now.month, year=now.year,
                                   defaults={'name': 'Piano Turni corrente', 'created_by': admin})

        self.stdout.write(self.style.SUCCESS('Seed data completed.'))
