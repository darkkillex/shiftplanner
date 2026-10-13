from django.conf import settings
from django.db import models


class EmployeeMedicalInfo(models.Model):
    """
    Prescrizioni mediche del dipendente (facoltative).

    Tenute in un modello separato da core.Employee di proposito: sono dati
    sanitari, quindi non devono comparire nelle API (/api/employees/), né
    nell'elenco dipendenti visibile a tutti gli utenti. Si leggono e si
    modificano solo dal Report commessa (staff/admin) e dall'admin.
    """
    employee = models.OneToOneField(
        "core.Employee",
        on_delete=models.CASCADE,
        related_name="medical_info",
        verbose_name="dipendente",
    )
    prescriptions = models.TextField("prescrizioni mediche", blank=True)
    updated_at = models.DateTimeField("ultima modifica", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="modificato da",
    )

    class Meta:
        verbose_name = "prescrizioni mediche"
        verbose_name_plural = "prescrizioni mediche"

    def __str__(self):
        return f"Prescrizioni — {self.employee}"
