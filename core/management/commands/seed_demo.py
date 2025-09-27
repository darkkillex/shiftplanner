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
            User.objects.create_superuser('admin','admin@example.com','admin')
            self.stdout.write(self.style.SUCCESS('Superuser admin/admin created.'))

        c, _ = Company.objects.get_or_create(name='ACME S.p.A.')
        for p in ['Infermiere', 'OSS', 'Tecnico', 'Magazziniere']:
            Profession.objects.get_or_create(name=p)

        employees = [
            ('Mario','Rossi','ACM001','mario.rossi@example.com'),
            ('Giulia','Bianchi','ACM002','giulia.bianchi@example.com'),
            ('Luca','Verdi','ACM003','luca.verdi@example.com'),
        ]
        for fn, ln, mat, em in employees:
            Employee.objects.get_or_create(first_name=fn,last_name=ln,matricola=mat,email=em, defaults={'company': c})

        ShiftType.objects.get_or_create(code='M', defaults={'label':'Mattino','start_time':time(6,0),'end_time':time(14,0)})
        ShiftType.objects.get_or_create(code='P', defaults={'label':'Pomeriggio','start_time':time(14,0),'end_time':time(22,0)})
        ShiftType.objects.get_or_create(code='N', defaults={'label':'Notte','start_time':time(22,0),'end_time':time(6,0)})

        now = timezone.localdate()
        admin = User.objects.get(username='admin')
        Plan.objects.get_or_create(month=now.month, year=now.year, defaults={'name':'Piano corrente','created_by':admin})

        self.stdout.write(self.style.SUCCESS('Seed data completed.'))
