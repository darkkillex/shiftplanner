from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Company, Profession, Employee, ShiftType,
    Plan, Assignment,
    Template, TemplateRow, PlanRow, Reminder
)
from calendar import monthrange
from django.db import transaction
from django import forms
from django.db.models import F
from django.template.response import TemplateResponse

import datetime as dt

# ---------------- Base ----------------

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'last_name', 'first_name', 'matricola', 'phone', 'email', 'is_active')
    search_fields = ('last_name', 'first_name', 'matricola', 'phone', 'email')
    filter_horizontal = ('professions',)

@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'label', 'start_time', 'end_time')
    search_fields = ('code', 'label')

# ---------------- Template + Righe ----------------
class InsertRowForm(forms.Form):
    position = forms.IntegerField(min_value=1, label="Posizione (order)")
    duty = forms.CharField(required=False, label="Mansione")
    is_spacer = forms.BooleanField(required=False, initial=False, label="Spacer")
    notes = forms.CharField(required=False, widget=forms.Textarea, label="Note")


class TemplateRowInline(admin.TabularInline):
    model = TemplateRow
    extra = 0
    fields = ('order', 'duty', 'is_spacer', 'notes')
    ordering = ('order',)
    sortable_field_name = 'order'  # drag&drop se supportato dal tema admin

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active', 'rows_count')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [TemplateRowInline]
    actions = ['clona_template', 'normalize_orders', 'propagate_layout', 'inserisci_riga_posizione']

    def rows_count(self, obj):
        return obj.rows.count()

    @admin.action(description="Clona template selezionati")
    def clona_template(self, request, queryset):
        for tpl in queryset:
            copy = Template.objects.create(
                name=f"{tpl.name} (copia)",
                is_active=tpl.is_active
            )
            rows = [
                TemplateRow(
                    template=copy,
                    order=r.order,
                    duty=r.duty,
                    is_spacer=r.is_spacer,
                    notes=r.notes
                )
                for r in tpl.rows.all().order_by('order', 'id')
            ]
            if rows:
                TemplateRow.objects.bulk_create(rows)
        self.message_user(request, f"Clonati {queryset.count()} template.")

    @admin.action(description="Rinumera righe (1..N) per ordine attuale")
    def normalize_orders(self, request, queryset):
        with transaction.atomic():
            for tpl in queryset.prefetch_related("rows"):
                for i, r in enumerate(tpl.rows.order_by("order", "id"), start=1):
                    if r.order != i:
                        r.order = i
                        r.save(update_fields=["order"])
        self.message_user(request, "Righe rinumerate.")

    @admin.action(description="Propaga layout ai piani che usano il template")
    def propagate_layout(self, request, queryset):
        from .models import PlanRow, Plan, Profession
        created_rows = 0
        updated_rows = 0

        with transaction.atomic():
            for tpl in queryset:
                # normalizza ordine nel template
                changed = False
                for i, r in enumerate(tpl.rows.order_by("order", "id"), start=1):
                    if r.order != i:
                        r.order = i
                        r.save(update_fields=["order"])
                        changed = True
                if changed:
                    tpl.refresh_from_db()

                tpl_rows = list(
                    tpl.rows.order_by("order", "id")
                           .values("order", "duty", "is_spacer", "notes")
                )

                plans = Plan.objects.filter(template=tpl).prefetch_related("rows")
                for plan in plans:
                    existing_by_order = {r.order: r for r in plan.rows.all()}

                    for tr in tpl_rows:
                        order = tr["order"]
                        duty = (tr["duty"] or "").strip()
                        is_spacer = bool(tr["is_spacer"])
                        notes = tr["notes"]

                        pr = existing_by_order.get(order)
                        if pr:
                            changed_pr = False
                            if pr.is_spacer != is_spacer:
                                pr.is_spacer = is_spacer; changed_pr = True
                            if pr.duty != duty:
                                pr.duty = duty; changed_pr = True
                            if pr.notes != notes:
                                pr.notes = notes; changed_pr = True
                            if changed_pr:
                                pr.save(update_fields=["is_spacer", "duty", "notes"])
                                updated_rows += 1
                        else:
                            PlanRow.objects.create(
                                plan=plan, order=order, duty=duty,
                                is_spacer=is_spacer, notes=notes
                            )
                            created_rows += 1

                        if duty:
                            Profession.objects.get_or_create(name=duty)

        self.message_user(
            request,
            f"Propagazione completata. Create {created_rows} righe, aggiornate {updated_rows}."
        )

    @admin.action(description="Inserisci riga a posizione K + propaga")
    def inserisci_riga_posizione(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Seleziona un solo Template.", level='warning')
            return
        tpl = queryset.first()

        if request.method == "POST" and request.POST.get("apply") == "1":
            form = InsertRowForm(request.POST)
            if form.is_valid():
                k = form.cleaned_data['position']
                duty = (form.cleaned_data['duty'] or '').strip()
                is_spacer = bool(form.cleaned_data['is_spacer'])
                notes = form.cleaned_data['notes'] or ''

                max_pos = tpl.rows.count() + 1
                if k > max_pos: k = max_pos
                if k < 1: k = 1

                with transaction.atomic():
                    # shift delle righe esistenti
                    TemplateRow.objects.filter(template=tpl, order__gte=k).update(order=F('order') + 1)
                    # inserimento riga
                    TemplateRow.objects.create(
                        template=tpl,
                        order=k,
                        duty='' if is_spacer else duty,
                        is_spacer=is_spacer,
                        notes=notes
                    )
                    # normalizza e propaga
                    self.normalize_orders(request, Template.objects.filter(pk=tpl.pk))
                    self.propagate_layout(request, Template.objects.filter(pk=tpl.pk))

                self.message_user(request, f"Inserita riga in posizione {k} e propagato layout.")
                return

        else:
            form = InsertRowForm(initial={'position': tpl.rows.count() + 1})

        context = {
            'form': form,
            'template_obj': tpl,
            'opts': self.model._meta,
            'title': "Inserisci riga a posizione K",
        }
        return TemplateResponse(request, 'admin/core/template/insert_row.html', context)

# ---------------- Plan Clonazione + Righe ----------------

class PlanRowInline(admin.TabularInline):
    model = PlanRow
    extra = 0
    fields = ('order', 'duty', 'is_spacer', 'notes')
    ordering = ('order',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id','name','month','year','status','created_by','revision','template')
    list_filter = ('year','month','status','template')
    search_fields = ('name',)
    ordering = ('-year','-month','name')
    inlines = [PlanRowInline]
    actions = ['clona_piano_struttura', 'clona_piano_completo']

    def _next_free_month_year(self, start_m, start_y):
        m, y = start_m, start_y
        while Plan.objects.filter(month=m, year=y).exists():
            m += 1
            if m == 13:
                m = 1
                y += 1
        return m, y

    def _clone_rows(self, src_plan, dst_plan):
        rows = [
            PlanRow(
                plan=dst_plan, order=r.order, duty=r.duty,
                is_spacer=r.is_spacer, notes=r.notes
            ) for r in src_plan.rows.all().order_by('order')
        ]
        if rows:
            PlanRow.objects.bulk_create(rows)

    def _clone_assignments(self, src_plan, dst_plan):
        last_day = monthrange(dst_plan.year, dst_plan.month)[1]
        new_items = []
        for a in src_plan.assignments.select_related('employee','shift_type','profession'):
            day = min(a.date.day, last_day)
            new_date = dt.date(dst_plan.year, dst_plan.month, day)
            new_items.append(Assignment(
                plan=dst_plan,
                profession=a.profession,
                date=new_date,
                employee=a.employee,
                shift_type=a.shift_type,
                notes=a.notes or '',
            ))
        if new_items:
            Assignment.objects.bulk_create(new_items)

    @transaction.atomic
    def clona_piano_struttura(self, request, queryset):
        created = 0
        for p in queryset:
            m, y = self._next_free_month_year(p.month, p.year)
            newp = Plan.objects.create(
                month=m, year=y,
                name=f"{p.name} (copia {m:02d}/{y})",
                status='Draft', created_by=request.user,
                revision=0, template=p.template
            )
            self._clone_rows(p, newp)
            created += 1
        self.message_user(request, f"Clonati {created} piani (solo struttura).")
    clona_piano_struttura.short_description = "Clona piano (solo struttura) nel primo mese libero"

    @transaction.atomic
    def clona_piano_completo(self, request, queryset):
        created = 0
        for p in queryset:
            m, y = self._next_free_month_year(p.month, p.year)
            newp = Plan.objects.create(
                month=m, year=y,
                name=f"{p.name} (copia {m:02d}/{y})",
                status='Draft', created_by=request.user,
                revision=0, template=p.template
            )
            self._clone_rows(p, newp)
            self._clone_assignments(p, newp)
            created += 1
        self.message_user(request, f"Clonati {created} piani (struttura + assegnazioni).")
    clona_piano_completo.short_description = "Clona piano (con assegnazioni) nel primo mese libero"

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'profession', 'date', 'employee', 'shift_type')
    list_filter = ('plan', 'profession', 'date', 'shift_type')
    search_fields = ('employee__first_name', 'employee__last_name', 'profession__name')


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'date',
        'title',
        'status_badge',   # badge colorato
        'created_by',
        'created_at',
        'closed_by',
        'closed_at',
    )
    # ordinamento di default: prima da fare/completate, poi per data
    ordering = ('completed', 'date', 'title')

    list_filter = (
        'completed',
        'date',
        'created_by',
        'closed_by',
    )
    search_fields = ('title', 'details')

    readonly_fields = (
        'created_by',
        'created_at',
        'closed_by',
        'closed_at',
    )

    actions = ['segna_completati', 'segna_da_fare']

    # ---------- Azioni ----------
    def segna_completati(self, request, queryset):
        n = queryset.update(completed=True)
        self.message_user(request, f"Segnati completati: {n}")
    segna_completati.short_description = "Segna come completati"

    def segna_da_fare(self, request, queryset):
        n = queryset.update(completed=False, closed_by=None, closed_at=None)
        self.message_user(request, f"Reimpostati da fare: {n}")
    segna_da_fare.short_description = "Segna come da fare"

    # ---------- Badge colorato ----------
    def status_badge(self, obj):
        """
        Restituisce un badge colorato in base allo stato:
        - Verde: completata
        - Rosso: scaduta
        - Giallo: in scadenza (≤ 3 giorni)
        - Blu: normale
        """
        today = dt.date.today()
        label = ""
        color = ""
        text = ""

        if obj.completed:
            label = "Completata"
            color = "#4caf50"   # verde
            text = "#fff"
        else:
            if obj.date < today:
                label = "Scaduta"
                color = "#e53935"  # rosso
                text = "#fff"
            else:
                days_diff = (obj.date - today).days
                if days_diff <= 3:
                    label = "In scadenza"
                    color = "#f9a825"  # giallo
                    text = "#000"
                else:
                    label = "Attiva"
                    color = "#1e88e5"  # blu
                    text = "#fff"

        return format_html(
            '<span style="display:inline-block;'
            'padding:2px 8px;border-radius:12px;'
            'background:{};color:{};font-size:0.8rem;">{}</span>',
            color, text, label
        )

    status_badge.short_description = "Stato"
    status_badge.admin_order_field = "completed"

    # ---------- Salvataggio ----------
    def save_model(self, request, obj, form, change):
        """
        - Se si crea una nota dall’admin → created_by = utente corrente (se non già impostato)
        - Se da admin si passa completata = True e non c'è closed_by → chi la salva diventa closed_by
        - Se si riapre (completed = False) → azzera closed_by/closed_at
        """
        if not obj.pk:
            # Creazione da admin
            if not obj.created_by:
                obj.created_by = request.user
        else:
            if "completed" in form.cleaned_data:
                completed_new = form.cleaned_data["completed"]
                if completed_new and not obj.closed_by:
                    obj.closed_by = request.user
                    if not obj.closed_at:
                        obj.closed_at = dt.datetime.now()
                if not completed_new:
                    obj.closed_by = None
                    obj.closed_at = None

        super().save_model(request, obj, form, change)
