from django.db import models
from django.conf import settings

class Company(models.Model):
    name = models.CharField(max_length=120, unique=True)
    def __str__(self): return self.name

class Profession(models.Model):
    name = models.CharField(max_length=120, unique=True)
    def __str__(self): return self.name

class Employee(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)
    matricola = models.CharField(max_length=40, unique=True)
    email = models.EmailField(unique=True)
    professions = models.ManyToManyField(Profession, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['last_name', 'first_name']
    def __str__(self): return f"{self.last_name} {self.first_name}"
    def full_name(self): return f"{self.last_name} {self.first_name}"


class ShiftType(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=60)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['id']
    def __str__(self): return f"{self.code} - {self.label}"


class Plan(models.Model):
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=120, default="", blank=True)
    status = models.CharField(max_length=12, choices=[('Draft','Draft'),('Published','Published')], default='Draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=0)
    template = models.ForeignKey(
        "Template",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="plans"
    )

    class Meta:
        unique_together = ('month','year')
    def __str__(self): return f"{self.name or 'Piano'} {self.month:02d}/{self.year}"

class PlanNotification(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='notifications')
    revision = models.PositiveIntegerField()
    sent_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Assignment(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='assignments')
    profession = models.ForeignKey(Profession, on_delete=models.PROTECT)
    date = models.DateField()
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    shift_type = models.ForeignKey(ShiftType, on_delete=models.PROTECT, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    class Meta:
        unique_together = ('plan','profession','date')

class Template(models.Model):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TemplateRow(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="rows")
    order = models.PositiveIntegerField(db_column='row_order')
    duty = models.CharField(max_length=120, blank=True) # mansione, può essere vuota
    is_spacer = models.BooleanField(default=False)      # riga vuota / separatore
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["template", "order"], name="uniq_template_order"),
        ]

    def __str__(self):
        return self.duty or "(spazio)"

class PlanRow(models.Model):
    plan = models.ForeignKey('Plan', on_delete=models.CASCADE, related_name='rows')
    order = models.PositiveIntegerField(db_column='row_order')  # evita parola riservata
    duty = models.CharField(max_length=120, blank=True)
    is_spacer = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'order'], name='uniq_plan_order'),
        ]
        indexes = [models.Index(fields=['plan', 'order'])]


class Reminder(models.Model):
    date = models.DateField()                 # giorno sul calendario
    title = models.CharField(max_length=160)  # testo breve
    details = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["date", "completed"])]
        ordering = ["date", "completed", "title"]

    def __str__(self): return f"{self.date} - {self.title}"
