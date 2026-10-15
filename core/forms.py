from django import forms
from .models import Plan, Template, Employee, ShiftType
import datetime as dt

class PlanCreateForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "month", "year", "status", "template"]

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
        # nome template obbligatorio
        self.fields["name"].required = True

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
        label="Righe del template (una mansione per riga, righe vuote = separatori)",
        widget=forms.Textarea(attrs={
            "class": "materialize-textarea monospace z-depth-1",
            "rows": 24,                 # altezza
            "style": "min-height:520px;height:520px;resize:vertical;",
            "placeholder": "Ufficio.1\nUfficio.2\n\nMagazzino.1\nMagazzino\n...",
            "spellcheck": "false",
            "autocomplete": "off",
            "autocapitalize": "off",
            "autocorrect": "off",
        })
    )

    class Meta:
        model = Template
        fields = ["name", "is_active"]


class TurnPatternForecastForm(forms.Form):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True).order_by("last_name", "first_name"),
        label="Dipendente",
    )
    shift_type = forms.ModelChoiceField(
        queryset=ShiftType.objects.order_by("code"),
        label="Turno (ShiftType)",
    )
    work_days = forms.IntegerField(
        min_value=1,
        max_value=31,
        label="Giorni lavorativi consecutivi",
        help_text="Es. 4 per pattern 4/2 (4 lavoro, 2 riposo)",
    )
    rest_days = forms.IntegerField(
        min_value=1,
        max_value=31,
        label="Giorni di riposo consecutivi",
        help_text="Es. 2 per pattern 4/2 (4 lavoro, 2 riposo)",
    )
    start_date = forms.DateField(
        label="Data di partenza",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    end_year = forms.IntegerField(
        min_value=2024,
        max_value=2100,
        label="Anno fino al quale generare",
        help_text="La turnazione verrà generata fino al 31/12 di questo anno",
    )
    skip_holidays = forms.BooleanField(
        required=False,
        label="Escludi festività italiane dal conteggio del pattern",
        help_text="Se attivo, i festivi diventano sempre giorni di riposo e non consumano i giorni di lavoro del pattern.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # garantiamo che in GET/POST il queryset sia aggiornato
        self.fields["employee"].queryset = (
            Employee.objects.filter(is_active=True)
            .order_by("last_name", "first_name")
        )
        self.fields["shift_type"].queryset = ShiftType.objects.order_by("code")

        # opzionale: se vuoi usare la select “normale” ed evitare problemi con Materialize,
        # scommenta queste due righe per avere le dropdown standard del browser:
        self.fields["employee"].widget.attrs.setdefault("class", "browser-default")
        self.fields["shift_type"].widget.attrs.setdefault("class", "browser-default")

    def clean(self):
        data = super().clean()
        start = data.get("start_date")
        end_year = data.get("end_year")
        if start and end_year and end_year < start.year:
            raise forms.ValidationError("L'anno finale deve essere >= anno della data di partenza.")
        return data