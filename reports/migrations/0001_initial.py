from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeMedicalInfo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prescriptions", models.TextField(blank=True, verbose_name="prescrizioni mediche")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="ultima modifica")),
                ("employee", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="medical_info", to="core.employee", verbose_name="dipendente")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="modificato da")),
            ],
            options={
                "verbose_name": "prescrizioni mediche",
                "verbose_name_plural": "prescrizioni mediche",
            },
        ),
    ]
