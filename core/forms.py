from django import forms
from .models import Plan, Template
import datetime as dt

class PlanCreateForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "month", "year", "status", "template"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "browser-default",
                "placeholder": "Es. Piano Reparto A"
            }),
            # month, year, status li settiamo in __init__ come Select
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Template piano turni: lista solo quelli attivi
        templates = Template.objects.filter(is_active=True).order_by("name")
        self.fields["template"] = forms.ModelChoiceField(
            queryset=templates,
            required=False,
            label="Template di riferimento",
            widget=forms.Select(attrs={"class": "browser-default"})
        )
        # Mese: numeri 1..12
        self.fields["month"] = forms.ChoiceField(
            choices=[(i, str(i)) for i in range(1, 13)],
            widget=forms.Select(attrs={"class": "browser-default"})
        )

        # Anno: da 2025 fino a (anno attuale + 5)
        now = dt.date.today()
        start = 2025
        end = max(now.year, 2025) + 5
        self.fields["year"] = forms.ChoiceField(
            choices=[(y, str(y)) for y in range(start, end + 1)],
            widget=forms.Select(attrs={"class": "browser-default"})
        )

        # Stato: valori del model, etichette in ITA
        self.fields["status"] = forms.ChoiceField(
            choices=[("Draft", "Bozza"), ("Published", "Pubblicato")],
            widget=forms.Select(attrs={"class": "browser-default"})
        )

        # iniziali comode
        self.fields["month"].initial = now.month
        self.fields["year"].initial = max(now.year, 2025)
        self.fields["status"].initial = "Draft"

        # etichette
        self.fields["name"].label = "Nome piano"
        self.fields["month"].label = "Mese"
        self.fields["year"].label = "Anno"
        self.fields["status"].label = "Stato"

    def clean(self):
        cleaned = super().clean()
        month = int(cleaned.get("month") or 0)
        year = int(cleaned.get("year") or 0)
        if month and year:
            from .models import Plan
            qs = Plan.objects.filter(month=month, year=year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Esiste già un piano per questo mese/anno.")
        return cleaned

class TemplateCreateForm(forms.ModelForm):
    """
    Form per creare un Template di piano turni.
    L’utente inserisce le mansioni riga per riga.
    Le righe vuote saranno considerate spazi vuoti nel piano.
    """
    rows_text = forms.CharField(
        label="Mansioni (una per riga — lascia vuote per spazi)",
        widget=forms.Textarea(attrs={
            "rows": 14,
            "class": "browser-default",
            "placeholder": "Esempio:\nACAM\nBO-1\nBO-2\n\nCoordinatore COVA\n\nDelegato ai Lavori",
        }),
        help_text="Ogni riga corrisponde a una cella della prima colonna del piano turni."
    )

    class Meta:
        model = Template
        fields = ["name", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "browser-default",
                "placeholder": "Nome template (es. Reparto A - Settimana)"
            })
        }
        labels = {
            "name": "Nome del template",
            "is_active": "Attivo"
        }