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
    created_by_name = serializers.SerializerMethodField()
    closed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Reminder
        fields = [
            "id",
            "date",
            "title",
            "details",
            "completed",
            "created_by",
            "created_at",
            "closed_by",
            "closed_at",
            "created_by_name",
            "closed_by_name",
        ]
        read_only_fields = [
            "created_by",
            "created_at",
            "closed_by",
            "closed_at",
            "created_by_name",
            "closed_by_name",
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return ""
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_closed_by_name(self, obj):
        if not obj.closed_by:
            return ""
        return obj.closed_by.get_full_name() or obj.closed_by.username

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        completed_prev = instance.completed
        completed_new = validated_data.get("completed", completed_prev)

        if "completed" in validated_data:
            if completed_new and not completed_prev:
                # chiusura
                request = self.context.get("request")
                if request and request.user.is_authenticated:
                    instance.closed_by = request.user
                instance.closed_at = dt.datetime.now()
            elif not completed_new and completed_prev:
                # riapertura
                instance.closed_by = None
                instance.closed_at = None

        return super().update(instance, validated_data)