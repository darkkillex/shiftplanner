from io import BytesIO
from zipfile import ZipFile

from django.http import HttpResponse
from django.utils.timezone import localtime

def generate_forecast_zip(employee, shift_type, start_date, end_year, work_days, rest_days, skip_holidays, attachments):
    """
    Crea uno ZIP in memoria con:
    - README.txt (parametri previsione + timestamp Europe/Rome)
    - tutti i PDF generati (attachments)
    """
    buffer = BytesIO()

    now = localtime()
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S %Z")

    skip_str = "Sì" if skip_holidays else "No"

    readme = (
        "Previsione turnazione Kairos\n"
        "---------------------------------\n"
        f"Generata il: {timestamp}\n\n"
        f"Dipendente: {employee.full_name()}\n"
        f"Email: {employee.email or '-'}\n\n"
        f"Turno di partenza: {shift_type.code} - {shift_type.label}\n"
        f"Pattern: Lavoro {work_days} / Riposo {rest_days}\n"
        f"Skip festività italiane: {skip_str}\n"
        f"Periodo: da {start_date.strftime('%d/%m/%Y')} "
        f"fino al 31/12/{end_year}\n"
    )

    with ZipFile(buffer, 'w') as z:
        z.writestr("README.txt", readme)

        for fname, content, ctype in attachments:
            z.writestr(fname, content)

    buffer.seek(0)
    return buffer
