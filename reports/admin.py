from django.contrib import admin

from core.models import Employee

from .models import EmployeeMedicalInfo


@admin.register(EmployeeMedicalInfo)
class EmployeeMedicalInfoAdmin(admin.ModelAdmin):
    list_display = ("employee", "short_text", "updated_at", "updated_by")
    search_fields = ("employee__last_name", "employee__first_name", "prescriptions")
    autocomplete_fields = ("employee",)
    readonly_fields = ("updated_at", "updated_by")

    @admin.display(description="Prescrizioni")
    def short_text(self, obj):
        t = obj.prescriptions or ""
        return t if len(t) <= 80 else t[:77] + "…"

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class EmployeeMedicalInfoInline(admin.StackedInline):
    model = EmployeeMedicalInfo
    extra = 0
    max_num = 1
    can_delete = True
    fields = ("prescriptions", "updated_at", "updated_by")
    readonly_fields = ("updated_at", "updated_by")


# Aggiunge le prescrizioni alla scheda Dipendente dell'admin senza toccare
# core/admin.py ('reports' è dopo 'core' in INSTALLED_APPS).
_employee_admin = admin.site._registry.get(Employee)
if _employee_admin is not None and EmployeeMedicalInfoInline not in _employee_admin.inlines:
    _employee_admin.inlines = [*_employee_admin.inlines, EmployeeMedicalInfoInline]

    _orig_save_formset = _employee_admin.save_formset

    def _save_formset(request, form, formset, change, _orig=_orig_save_formset):
        if formset.model is EmployeeMedicalInfo:
            for obj in formset.save(commit=False):
                obj.updated_by = request.user
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            formset.save_m2m()
            return
        return _orig(request, form, formset, change)

    _employee_admin.save_formset = _save_formset
