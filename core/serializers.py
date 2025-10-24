from rest_framework import serializers, viewsets
from .models import Company, Profession, Employee, ShiftType, Plan, Assignment, Reminder

import datetime as dt

class CompanySerializer(serializers.ModelSerializer):
    class Meta: model = Company; fields = '__all__'

class ProfessionSerializer(serializers.ModelSerializer):
    class Meta: model = Profession; fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='full_name', read_only=True)
    class Meta:
        model = Employee
        fields = ['id','first_name','last_name','company','matricola','email','is_active','full_name','professions']

class ShiftTypeSerializer(serializers.ModelSerializer):
    class Meta: model = ShiftType; fields = '__all__'

class PlanSerializer(serializers.ModelSerializer):
    class Meta: model = Plan; fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    profession_name = serializers.CharField(source='profession.name', read_only=True)
    shift_code = serializers.CharField(source='shift_type.code', read_only=True)
    shift_label = serializers.CharField(source='shift_type.label', read_only=True)
    notes = serializers.CharField(read_only=True, allow_blank=True)
    has_note = serializers.SerializerMethodField()
    class Meta:
        model = Assignment
        fields = ['id','plan','profession','date','employee','shift_type',
                  'employee_name','profession_name','shift_code','shift_label',
                  'notes','has_note']

    def get_has_note(self, obj):
        return bool(obj.notes)


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = "__all__"
        read_only_fields = ("created_by", "created_at")


