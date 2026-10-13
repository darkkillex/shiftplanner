import datetime as dt
import json
import logging
import os

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.gzip import gzip_page
from django.views.decorators.http import require_GET, require_POST

from core.models import Employee

from .models import EmployeeMedicalInfo
from .presc_import import apply_plan, build_plan, read_file_prescriptions
from .source_excel import ExcelFormatError, build_from_excel
from .source_kairos import available_years, build_from_kairos, kairos_people_index

logger = logging.getLogger(__name__)

MAX_UPLOAD_MB = 60
ALLOWED_EXT = (".xlsx", ".xlsm")


def is_staff_or_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def staff_api(view):
    """Come user_passes_test, ma per le API risponde 403 JSON invece del redirect al login."""
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Autenticazione richiesta."}, status=401)
        if not is_staff_or_admin(request.user):
            return JsonResponse({"detail": "Funzione riservata a staff e amministratori."}, status=403)
        return view(request, *args, **kwargs)
    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return wrapped


def _json(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"separators": (",", ":"), "ensure_ascii": False})


@login_required
@user_passes_test(is_staff_or_admin)
def report_page(request):
    years = available_years()
    today = dt.date.today()
    default_year = today.year if today.year in years else (years[0] if years else today.year)
    return render(request, "reports/report_commessa.html", {
        "years": years or [today.year],
        "default_year": default_year,
        "max_upload_mb": MAX_UPLOAD_MB,
    })


@require_GET
@staff_api
@gzip_page
def kairos_dataset(request):
    """GET ?year=2026&from=1&to=12 -> dataset normalizzato dai piani Kairos."""
    try:
        year = int(request.GET.get("year") or dt.date.today().year)
        m_from = int(request.GET.get("from") or 1)
        m_to = int(request.GET.get("to") or 12)
    except ValueError:
        return _json({"detail": "Parametri non validi."}, status=400)
    if not (1 <= m_from <= 12 and 1 <= m_to <= 12 and m_from <= m_to):
        return _json({"detail": "Intervallo di mesi non valido."}, status=400)
    return _json(build_from_kairos(year, m_from, m_to))


@require_POST
@staff_api
@gzip_page
def excel_dataset(request):
    """POST multipart 'file' -> dataset normalizzato dal piano turni Excel (non salva nulla)."""
    f, name = _uploaded_excel(request)
    if f is None:
        return name
    try:
        data = build_from_excel(f, name, kairos_people_index())
    except ExcelFormatError as exc:
        return _json({"detail": str(exc)}, status=400)
    except Exception:
        logger.exception("Report commessa: errore nella lettura del file %s", name)
        return _json({"detail": "Errore imprevisto nella lettura del file. Controlla che sia il piano turni ATI."},
                     status=500)
    return _json(data)


def _uploaded_excel(request):
    """Valida il file caricato; restituisce (file, nome) oppure (None, JsonResponse di errore)."""
    f = request.FILES.get("file")
    if not f:
        return None, _json({"detail": "Nessun file ricevuto."}, status=400)
    name = os.path.basename(f.name or "piano.xlsx")
    if not name.lower().endswith(ALLOWED_EXT):
        return None, _json({"detail": "Formato non supportato: servono file .xlsx o .xlsm."}, status=400)
    if f.size > MAX_UPLOAD_MB * 1024 * 1024:
        return None, _json({"detail": f"File troppo grande (massimo {MAX_UPLOAD_MB} MB)."}, status=400)
    return f, name


@require_POST
@staff_api
def import_prescriptions(request):
    """
    POST multipart: file, mode=preview|apply, clear_missing=0|1
    Il piano viene sempre ricalcolato dal file: in 'apply' non ci si fida del client.
    """
    f, name = _uploaded_excel(request)
    if f is None:
        return name
    mode = request.POST.get("mode", "preview")
    clear_missing = request.POST.get("clear_missing") in ("1", "true", "on")
    try:
        plan = build_plan(read_file_prescriptions(f), clear_missing=clear_missing)
    except ExcelFormatError as exc:
        return _json({"detail": str(exc)}, status=400)
    out = plan.as_dict()
    if mode == "apply":
        out["applied"] = apply_plan(plan, request.user)
        logger.info("Prescrizioni importate da %s da %s: %s", name, request.user, out["applied"])
    return _json(out)


@require_POST
@staff_api
def save_prescriptions(request, employee_id: int):
    """POST {"text": "..."} -> salva le prescrizioni mediche del dipendente (vuoto = rimuove)."""
    emp = get_object_or_404(Employee, pk=employee_id)
    try:
        payload = json.loads(request.body or "{}")
    except ValueError:
        return _json({"detail": "JSON non valido."}, status=400)
    text = str(payload.get("text") or "").strip()
    if len(text) > 4000:
        return _json({"detail": "Testo troppo lungo (massimo 4000 caratteri)."}, status=400)
    info = EmployeeMedicalInfo.objects.filter(employee=emp).first()
    if not text:
        if info:
            info.delete()
        return _json({"ok": True, "text": ""})
    if info is None:
        info = EmployeeMedicalInfo(employee=emp)
    info.prescriptions = text
    info.updated_by = request.user
    info.save()
    return _json({"ok": True, "text": info.prescriptions})
