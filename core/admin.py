from django.contrib import admin
from .models import (
    Company, Profession, Employee, ShiftType,
    Plan, Assignment,
    Template, TemplateRow, PlanRow
)

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

# ---------------- Plan + Righe ----------------

class PlanRowInline(admin.TabularInline):
    model = PlanRow
    extra = 0
    fields = ('order', 'duty', 'is_spacer', 'notes')
    ordering = ('order',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'month', 'year', 'status', 'created_by', 'revision', 'template')
    list_filter = ('year', 'month', 'status', 'template')
    search_fields = ('name',)
    ordering = ('-year', '-month', 'name')
    inlines = [PlanRowInline]

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'profession', 'date', 'employee', 'shift_type')
    list_filter = ('plan', 'profession', 'date', 'shift_type')
    search_fields = ('employee__first_name', 'employee__last_name', 'profession__name')
