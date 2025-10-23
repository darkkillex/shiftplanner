from django.contrib import admin
from .models import (
    Company, Profession, Employee, ShiftType,
    Plan, Assignment,
    Template, TemplateRow, PlanRow
)
from calendar import monthrange
from django.db import transaction

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
    list_display = ('id', 'last_name', 'first_name', 'matricola', 'email', 'is_active')
    search_fields = ('last_name', 'first_name', 'matricola', 'email')
    filter_horizontal = ('professions',)

@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'label', 'start_time', 'end_time')
    search_fields = ('code', 'label')

# ---------------- Template + Righe ----------------

class TemplateRowInline(admin.TabularInline):
    model = TemplateRow
    extra = 1
    fields = ('order', 'duty', 'is_spacer', 'notes')
    ordering = ('order',)

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [TemplateRowInline]
    actions = ['clona_template']

    def clona_template(self, request, queryset):
        for tpl in queryset:
            copy = Template.objects.create(name=f"{tpl.name} (copia)", is_active=tpl.is_active)
            rows = [
                TemplateRow(
                    template=copy,
                    order=r.order,
                    duty=r.duty,
                    is_spacer=r.is_spacer,
                    notes=r.notes
                ) for r in tpl.rows.all().order_by('order')
            ]
            if rows:
                TemplateRow.objects.bulk_create(rows)
        self.message_user(request, f"Clonati {queryset.count()} template.")
    clona_template.short_description = "Clona template selezionati"

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
