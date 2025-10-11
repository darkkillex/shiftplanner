import calendar, datetime as dt
import logging

from io import BytesIO

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from email.utils import formataddr

from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

from .forms import PlanCreateForm
from .forms import TemplateCreateForm
from .models import Template, TemplateRow, Plan

from .serializers import *


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

        # preload assignments
        assignments = (Assignment.objects
                       .filter(plan=plan)
                       .select_related('employee', 'shift_type', 'profession'))
        idx = {(a.profession_id, a.date): a for a in assignments}

        # mappa nome->Profession (casefold per tolleranza)
        prof_by_name = {p.name.strip().casefold(): p for p in Profession.objects.all()}

        rows = []
        if plan.rows.exists():
            # Usa PlanRow (mansioni e spazi)
            for r in plan.rows.all().order_by('order'):
                if r.is_spacer:
                    label = ''
                    prof = None
                else:
                    label = r.duty
                    prof = prof_by_name.get((r.duty or '').strip().casefold())

                row = {
                    'profession_id': getattr(prof, 'id', None),
                    'profession': label,  # prima colonna: etichetta del template
                    'spacer': bool(r.is_spacer),
                }
                for d in range(1, days + 1):
                    day = dt.date(plan.year, plan.month, d)
                    if not prof:  # spacer o mansione non mappata a Profession
                        row[str(d)] = {
                            'employee_id': None, 'employee_name': '',
                            'shift_code': '', 'shift_label': '',
                            'notes': '', 'has_note': False
                        }
                    else:
                        a = idx.get((prof.id, day))
                        row[str(d)] = {
                            'employee_id': a.employee_id if a else None,
                            'employee_name': a.employee.full_name() if a else '',
                            'shift_code': a.shift_type.code if (a and a.shift_type) else '',
                            'shift_label': a.shift_type.label if (a and a.shift_type) else '',
                            'notes': a.notes if a and a.notes else '',
                            'has_note': bool(a and a.notes),
                        }
                rows.append(row)
        else:
            # Fallback: professioni alfabetiche
            for p in Profession.objects.order_by('name'):
                row = {'profession_id': p.id, 'profession': p.name, 'spacer': False}
                for d in range(1, days + 1):
                    day = dt.date(plan.year, plan.month, d)
                    a = idx.get((p.id, day))
                    row[str(d)] = {
                        'employee_id': a.employee_id if a else None,
                        'employee_name': a.employee.full_name() if a else '',
                        'shift_code': a.shift_type.code if (a and a.shift_type) else '',
                        'shift_label': a.shift_type.label if (a and a.shift_type) else '',
                        'notes': a.notes if a and a.notes else '',
                        'has_note': bool(a and a.notes)
                    }
                rows.append(row)

        return Response({'year': plan.year, 'month': plan.month, 'days': days, 'rows': rows})


    @action(detail=True, methods=['post'])
    def bulk_assign(self, request, pk=None):
        plan = self.get_object()
        employee_id = request.data.get('employee_id')
        shift_id = request.data.get('shift_type_id')
        cells = request.data.get('cells', [])
        note = (request.data.get('note') or '').strip()
        if not employee_id or not cells:
            return Response({'detail':'employee_id e cells obbligatori'}, status=400)

        # --- Check conflitti: stesso plan, stesse date, stesso employee ma su ALTRE professioni
        # Costruiamo mappa date -> set di profession_id target (per escludere i casi in cui sta già nella stessa cella)
        targets_by_date = {}
        for c in cells:
            try:
                pid = int(c['profession_id'])
                d = str(c['date'])
            except Exception:
                return Response({'detail': f'Formato cella non valido: {c}'}, status=status.HTTP_400_BAD_REQUEST)
            targets_by_date.setdefault(d, set()).add(pid)

        dates = list(targets_by_date.keys())
        # tutto ciò che è già assegnato a questo employee nelle stesse date
        conflicts_qs = (
            Assignment.objects
            .filter(plan=plan, date__in=dates, employee_id=employee_id)
            .select_related('profession', 'shift_type')
        )

        # escludi i casi in cui è nella STESSA cella (stessa professione)
        conflicts = []
        for a in conflicts_qs:
            d_iso = a.date.isoformat()
            if a.profession_id in targets_by_date.get(d_iso, set()):
                continue  # stessa cella: ok
            conflicts.append({
                'date': d_iso,
                'profession_id': a.profession_id,
                'profession': a.profession.name,
                'shift_code': a.shift_type.code if a.shift_type else '',
                'shift_label': a.shift_type.label if a.shift_type else '',
            })

        if conflicts:
            return Response(
                {
                    'detail': 'Il lavoratore risulta già assegnato in altre posizioni nelle date selezionate.',
                    'conflicts': conflicts
                },
                status=status.HTTP_409_CONFLICT
            )

        # --- Nessun conflitto: procedi in transazione (all-or-nothing)
        with transaction.atomic():
            for c in cells:
                obj, _ = Assignment.objects.update_or_create(
                    plan=plan,
                    profession_id=c['profession_id'],
                    date=c['date'],
                    defaults={'employee_id': employee_id, 'shift_type_id': shift_id}
                )
                # aggiorna/impone la nota (anche quando la riassegni)
                obj.notes = note
                obj.save(update_fields=['notes'])

        return Response({'updated': len(cells)}, status=200)

    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        plan = self.get_object()
        logger = logging.getLogger(__name__)

        # 1) bump revisione in modo atomico
        with transaction.atomic():
            Plan.objects.select_for_update().filter(pk=plan.pk).update(revision=F('revision') + 1)
        plan.refresh_from_db()
        rev_str = f"Rev.{plan.revision:02d}"

        sender_name = request.user.get_full_name() or request.user.username

        qs = (Assignment.objects
              .filter(plan=plan, employee__email__isnull=False)
              .exclude(employee__email='')
              .select_related('employee', 'shift_type', 'profession'))

        by_emp = {}
        for a in qs:
            by_emp.setdefault(a.employee, []).append(a)

        prepared = len(by_emp)
        if not prepared:
            return Response(
                {'prepared': 0, 'sent': 0, 'rev': plan.revision, 'detail': 'Nessun destinatario con email.'},
                status=200)

        month_number = dt.date(plan.year, plan.month, 1).strftime('%m')
        legend = list(ShiftType.objects.values_list('code', 'label'))

        sent = 0
        for emp, items in by_emp.items():
            items.sort(key=lambda x: x.date)
            rows = [{
                'weekday': ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'][a.date.weekday()],
                'date': a.date.strftime('%d/%m/%Y'),
                "profession_name": a.profession.name,
                'shift_label': (a.shift_type.label if a.shift_type else ''),
                'notes': a.notes or '',
            } for a in items]

            ctx = {
                'employee_name': emp.full_name(),
                'month_number': month_number,
                'year': plan.year,
                'legend': legend,
                'assignments': rows,
                'app_url': f"{settings.APP_BASE_URL}/plan/{plan.pk}/",
                'reply_to_email': getattr(settings, 'REPLY_TO_EMAIL',
                                          settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER),
                'revision_str': rev_str,
                'sender_name': sender_name,
            }

            # Oggetto con Rev + nome e cognome
            subject = f"Piano turni {plan.month:02d}/{plan.year} {rev_str} - {emp.full_name()}"
            from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
            reply_to = [settings.REPLY_TO_EMAIL] if getattr(settings, 'REPLY_TO_EMAIL', None) else None

            text_body = render_to_string("emails/plan_personal.txt", ctx)
            html_body = render_to_string("emails/plan_personal.html", ctx)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=[formataddr((emp.full_name(), emp.email))],
                reply_to=reply_to
            )
            msg.attach_alternative(html_body, "text/html")

            try:
                n = msg.send(fail_silently=False)
                sent += (1 if n else 0)
                if not n:
                    logger.warning("Email non inviata (send()=0) a %s <%s>", emp.full_name(), emp.email)
            except Exception as e:
                logger.exception("Errore invio a %s <%s>: %s", emp.full_name(), emp.email, e)

        # (Opzionale) salva log invio se hai il modello PlanNotification
        try:
            from .models import PlanNotification  # solo se esiste
            PlanNotification.objects.create(plan=plan, revision=plan.revision, sent_count=sent)
        except Exception:
            pass

        return Response({'prepared': prepared, 'sent': sent, 'rev': plan.revision}, status=200)

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


    @action(detail=True, methods=['post'])
    def set_note(self, request, pk=None):
        """
        Imposta/aggiorna/azzera la nota su una cella (deve esistere un Assignment).
        Body: { profession_id: int, date: 'YYYY-MM-DD', note: '...' }
        """
        plan = self.get_object()
        try:
            prof_id = int(request.data.get('profession_id'))
            day = dt.date.fromisoformat(request.data.get('date'))
        except Exception:
            return Response({'detail': 'profession_id/date non validi'}, status=status.HTTP_400_BAD_REQUEST)

        note = (request.data.get('note') or '').strip()

        try:
            a = Assignment.objects.get(plan=plan, profession_id=prof_id, date=day)
        except Assignment.DoesNotExist:
            return Response({'detail': 'Nessuna assegnazione su questa cella. Assegna un lavoratore prima di aggiungere una nota.'},
                            status=status.HTTP_400_BAD_REQUEST)

        a.notes = note  # può essere stringa vuota per rimuovere la nota
        a.save(update_fields=['notes'])

        return Response({'ok': True, 'notes': a.notes, 'has_note': bool(a.notes)}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['get'])
    def export_xlsx(self, request, pk=None):
        plan = self.get_object()
        days = calendar.monthrange(plan.year, plan.month)[1]

        # Prepara workbook/worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = f"{plan.month:02d}-{plan.year}"

        # Stili base
        bold = Font(bold=True)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        wrap = Alignment(wrap_text=True)
        sunday_fill = PatternFill("solid", fgColor="FFEBEE")     # rosato leggero per domeniche
        header_fill = PatternFill("solid", fgColor="E3F2FD")     # azzurrino header

        # Header: A1 "Professione", poi 1..N con giorno + abbreviazione
        ws.cell(row=1, column=1, value="Professione").font = bold
        ws.cell(row=1, column=1).alignment = center
        ws.cell(row=1, column=1).fill = header_fill

        # mappa indice colonna -> (giorno, data)
        col_for_day = {}

        it_weekdays = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        for d in range(1, days+1):
            col = d + 1  # colonna 2..N
            the_date = dt.date(plan.year, plan.month, d)
            wd = it_weekdays[the_date.weekday()]
            ws.cell(row=1, column=col, value=f"{d}\n{wd}").font = bold
            ws.cell(row=1, column=col).alignment = center
            ws.cell(row=1, column=col).fill = header_fill
            if the_date.weekday() == 6:   # domenica
                ws.cell(row=1, column=col).fill = sunday_fill
            col_for_day[col] = the_date

        # -------- Layout righe: usa PlanRow se presenti, altrimenti Profession --------
        prof_by_name = {p.name.strip().casefold(): p for p in Profession.objects.all()}
        use_plan_rows = plan.rows.exists()
        if use_plan_rows:
            layout = []
            for r in plan.rows.all().order_by('order'):
                if r.is_spacer:
                    layout.append({'label': '', 'profession': None, 'spacer': True})
                else:
                    layout.append({
                        'label': r.duty,
                        'profession': prof_by_name.get((r.duty or '').strip().casefold()),
                        'spacer': False
                    })
        else:
            layout = [{'label': p.name, 'profession': p, 'spacer': False}
                      for p in Profession.objects.order_by('name')]

        # -------- Precarica assignments --------
        ass = (Assignment.objects
               .filter(plan=plan)
               .select_related('employee', 'shift_type', 'profession'))
        idx = {(a.profession_id, a.date): a for a in ass}

        # -------- Scrittura righe --------
        row = 2
        for item in layout:
            # Colonna A: etichetta del template (vuota per spacer)
            ws.cell(row=row, column=1, value=item['label'])

            # Celle giorno per giorno
            for d in range(1, days+1):
                col = d + 1
                day = col_for_day[col]

                # Spacer o mansione non mappata a Profession -> lascia vuoto
                if item['spacer'] or not item['profession']:
                    continue

                p = item['profession']
                a = idx.get((p.id, day))
                if not a:
                    continue

                name = a.employee.full_name()
                shift = f" ({a.shift_type.label})" if a.shift_type else ""
                cell = ws.cell(row=row, column=col, value=f"{name}{shift}")
                cell.alignment = wrap
                if a.notes:
                    try:
                        cell.comment = Comment(a.notes, "ShiftPlanner")
                    except Exception:
                        pass
            row += 1


        # layout
        ws.freeze_panes = "B2"
        ws.column_dimensions["A"].width = 40
        # larghezza base per giorni
        for col in range(2, days+2):
            ws.column_dimensions[get_column_letter(col)].width = 22

        # Output
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        fname = f"plan_{plan.year}_{plan.month:02d}.xlsx"
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

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
    employees = Employee.objects.order_by('last_name','first_name')
    shifts = ShiftType.objects.order_by('code')
    use_plan_rows = plan.rows.exists()
    return render(request, 'monthly_plan.html', {
        'plan': plan,
        'use_plan_rows': use_plan_rows,
        'employees': employees,
        'shifts': shifts,
    })

def logout_view(request):
    logout(request)
    return redirect('login')

def _is_staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
def functions_hub(request):
    return render(request, "functions_hub.html")

@login_required
@user_passes_test(_is_staff_or_superuser)
def plans_area(request):
    plans = Plan.objects.order_by("-year","-month","name")
    return render(request, "plans_area.html", {"plans": plans})

@login_required
@user_passes_test(_is_staff_or_superuser)
def templates_area(request):
    tpls = Template.objects.order_by("name")
    return render(request, "templates_area.html", {"templates": tpls})


@login_required
@user_passes_test(_is_staff_or_superuser)
def plan_create(request):
    if request.method == "POST":
        form = PlanCreateForm(request.POST)
        if form.is_valid():
            month = int(form.cleaned_data["month"])
            year = int(form.cleaned_data["year"])

            existing = Plan.objects.filter(month=month, year=year).first()
            if existing:
                messages.info(request, "Esiste già un piano per questo mese/anno. Apertura del piano esistente.")
                return redirect("monthly_plan", pk=existing.pk)

            plan = form.save(commit=False)
            plan.created_by = request.user
            plan.save()

            # --- Clona righe dal template, se selezionato ---
            template = form.cleaned_data.get("template")
            if template:
                from .models import TemplateRow, PlanRow
                rows = []
                for r in template.rows.all():
                    rows.append(PlanRow(
                        plan=plan,
                        order=r.order,
                        duty=r.duty,
                        is_spacer=r.is_spacer,
                        notes=r.notes
                    ))
                if rows:
                    PlanRow.objects.bulk_create(rows)

            messages.success(request, "Piano creato correttamente.")
            return redirect("monthly_plan", pk=plan.pk)
    else:
        form = PlanCreateForm()

    return render(request, "plan_create.html", {"form": form})


def _parse_rows(text: str):
    """Ritorna un elenco di TemplateRow da testo multilinea."""
    lines = text.replace("\r\n", "\n").split("\n")
    rows = []
    order = 1
    for ln in lines:
        stripped = ln.strip()
        if stripped == "":
            rows.append(TemplateRow(order=order, duty="", is_spacer=True))
        else:
            rows.append(TemplateRow(order=order, duty=stripped, is_spacer=False))
        order += 1
    # elimina eventuali spazi finali consecutivi
    while rows and rows[-1].is_spacer:
        rows.pop()
    return rows

@login_required
@user_passes_test(_is_staff_or_superuser)
@transaction.atomic
def template_create(request):
    """Form per creare un nuovo template di piano turni."""
    if request.method == "POST":
        form = TemplateCreateForm(request.POST)
        if form.is_valid():
            template = form.save()
            rows = _parse_rows(form.cleaned_data["rows_text"])
            for r in rows:
                r.template = template
            if rows:
                TemplateRow.objects.bulk_create(rows)
            messages.success(request, "Template creato correttamente.")
            return redirect("template_detail", pk=template.pk)
    else:
        form = TemplateCreateForm()
    return render(request, "template_create.html", {"form": form})


@login_required
@user_passes_test(_is_staff_or_superuser)
def template_detail(request, pk):
    """Visualizza un template e le sue righe."""
    template = get_object_or_404(Template.objects.prefetch_related("rows"), pk=pk)
    return render(request, "template_detail.html", {"template": template})