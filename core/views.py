from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import send_mass_mail
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import Company, Profession, Employee, ShiftType, Plan, Assignment
from .serializers import *
import calendar, datetime as dt

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('last_name','first_name')
    serializer_class = EmployeeSerializer

class ProfessionViewSet(viewsets.ModelViewSet):
    queryset = Profession.objects.all().order_by('name')
    serializer_class = ProfessionSerializer

class ShiftTypeViewSet(viewsets.ModelViewSet):
    queryset = ShiftType.objects.all().order_by('code')
    serializer_class = ShiftTypeSerializer

class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all().order_by('-year','-month')
    serializer_class = PlanSerializer

    @action(detail=True, methods=['get'])
    def grid(self, request, pk=None):
        plan = self.get_object()
        days = calendar.monthrange(plan.year, plan.month)[1]
        profs = list(Profession.objects.all().order_by('name'))
        assignments = Assignment.objects.filter(plan=plan).select_related('employee','shift_type','profession')
        idx = {(a.profession_id, a.date): a for a in assignments}
        rows = []
        for p in profs:
            row = {'profession_id': p.id, 'profession': p.name}
            for d in range(1, days+1):
                day = dt.date(plan.year, plan.month, d)
                a = idx.get((p.id, day))
                row[str(d)] = {
                    'employee_id': a.employee_id if a else None,
                    'employee_name': a.employee.full_name() if a else '',
                    'shift_code': a.shift_type.code if (a and a.shift_type) else '',
                    'shift_label': a.shift_type.label if (a and a.shift_type) else ''
                }
            rows.append(row)
        return Response({'year': plan.year, 'month': plan.month, 'days': days, 'rows': rows})

    @action(detail=True, methods=['post'])
    def bulk_assign(self, request, pk=None):
        plan = self.get_object()
        employee_id = request.data.get('employee_id')
        shift_id = request.data.get('shift_type_id')
        cells = request.data.get('cells', [])
        if not employee_id or not cells:
            return Response({'detail':'employee_id e cells obbligatori'}, status=400)
        with transaction.atomic():
            for c in cells:
                Assignment.objects.update_or_create(
                    plan=plan,
                    profession_id=c['profession_id'],
                    date=c['date'],
                    defaults={'employee_id': employee_id, 'shift_type_id': shift_id}
                )
        return Response({'updated': len(cells)}, status=200)

    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        plan = self.get_object()
        qs = Assignment.objects.filter(plan=plan).select_related('employee')
        by_emp = {}
        for a in qs:
            by_emp.setdefault(a.employee, 0)
            by_emp[a.employee] += 1
        messages = []
        subject = f"Piano turni {plan.month:02d}/{plan.year}"
        from_email = None
        for emp, count in by_emp.items():
            if not emp.email:
                continue
            body = f"Ciao {emp.full_name()},\n\nSono stati pubblicati {count} turni per il piano {plan.month:02d}/{plan.year}.\nAccedi all'app per i dettagli.\n\n— Ufficio Pianificazione"
            messages.append((subject, body, from_email, [emp.email]))
        if not messages:
            return Response({'detail':'Nessuna email inviata (nessun assegnato o email mancanti).'}, status=200)
        send_mass_mail(messages, fail_silently=False)
        return Response({'sent': len(messages)}, status=200)

    @action(detail=True, methods=['post'])
    def bulk_clear(self, request, pk=None):
        plan = self.get_object()
        cells = request.data.get('cells', [])
        if not isinstance(cells, list) or not cells:
            return Response({'detail': 'cells obbligatorio'}, status=status.HTTP_400_BAD_REQUEST)

        deleted = 0
        for c in cells:
            try:
                prof_id = int(c['profession_id'])
                day = dt.date.fromisoformat(c['date'])  # forza tipo date, niente ambiguità
            except Exception:
                return Response({'detail': f"Formato cella non valido: {c}"}, status=status.HTTP_400_BAD_REQUEST)

            n, _ = Assignment.objects.filter(
                plan=plan,
                profession_id=prof_id,
                date=day,
            ).delete()
            deleted += n

        return Response({'deleted': deleted}, status=status.HTTP_200_OK)


@login_required
def home(request):
    plans = Plan.objects.order_by('-year','-month')[:12]
    return render(request, 'home.html', {'plans': plans})

@login_required
def profile(request):
    user = request.user
    return render(request, 'profile.html', {
        'user_obj': user,
    })

@login_required
def monthly_plan(request, pk: int):
    plan = get_object_or_404(Plan, pk=pk)
    professions = Profession.objects.order_by('name').all()
    employees = Employee.objects.order_by('last_name','first_name').all()
    shifts = ShiftType.objects.order_by('code').all()
    return render(request, 'monthly_plan.html', {'plan': plan, 'professions': professions, 'employees': employees, 'shifts': shifts})

def logout_view(request):
    logout(request)
    return redirect('login')