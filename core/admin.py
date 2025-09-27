from django.contrib import admin
from .models import Company, Profession, Employee, ShiftType, Plan, Assignment

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ('name',)

@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id','last_name','first_name','matricola','email','is_active')
    search_fields = ('last_name','first_name','matricola','email')
    filter_horizontal = ('professions',)

@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ('id','code','label','start_time','end_time')

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id','name','month','year','status','created_by')
    list_filter = ('year','month','status')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id','plan','profession','date','employee','shift_type')
    list_filter = ('plan','profession','date','shift_type')
