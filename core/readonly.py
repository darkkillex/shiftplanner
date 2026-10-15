"""
Profilo "Sola lettura".

Un utente in sola lettura è staff (vede tutte le aree riservate allo staff)
ed è membro del gruppo READONLY_GROUP. Può consultare tutto e scaricare
gli XLSX dei piani e i CSV del Report commessa, ma non può modificare,
inserire, cancellare nulla né inviare email.

La garanzia è lato server (ReadOnlyMiddleware): ogni richiesta che non sia
di sola lettura (POST/PUT/PATCH/DELETE) viene rifiutata, salvo le poche
eccezioni innocue in WRITE_ALLOWED. Nell'interfaccia i comandi di modifica
vengono anche nascosti, ma la sicurezza non dipende da questo.
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import Resolver404, resolve

READONLY_GROUP = "Sola lettura"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# richieste POST consentite (non modificano dati e non inviano email)
WRITE_ALLOWED = {
    "password_change",            # cambio della propria password
    "reports:excel_dataset",      # analisi di un file Excel nel Report commessa (non salva nulla)
}
# consentito solo in anteprima (mode=preview); "apply" resta bloccato
WRITE_PREVIEW_ONLY = {"reports:import_prescriptions"}

# pagine che servono solo a creare/inviare: inutili in sola lettura
PAGES_BLOCKED = {
    "plan_create",
    "template_create",
    "turn_pattern_forecast",
    "turn_pattern_forecast_only_local_download",
}

DENY_MESSAGE = "Profilo in sola lettura: questa operazione non è consentita."


def is_readonly(user) -> bool:
    """True se l'utente è nel gruppo "Sola lettura" (i superuser non lo sono mai)."""
    if not getattr(user, "is_authenticated", False) or user.is_superuser:
        return False
    cached = getattr(user, "_kairos_readonly", None)
    if cached is None:
        cached = user.groups.filter(name=READONLY_GROUP).exists()
        user._kairos_readonly = cached
    return cached


def _view_name(request):
    try:
        return resolve(request.path_info).view_name
    except Resolver404:
        return None


def _wants_json(request) -> bool:
    path = request.path_info
    return (path.startswith("/api/") or "/api/" in path
            or "application/json" in request.headers.get("Accept", "")
            or request.headers.get("X-Requested-With") == "XMLHttpRequest")


class ReadOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and is_readonly(user):
            name = _view_name(request)
            if request.method not in SAFE_METHODS:
                allowed = name in WRITE_ALLOWED or (
                    name in WRITE_PREVIEW_ONLY and request.POST.get("mode", "preview") == "preview")
                if not allowed:
                    return self.deny(request)
            elif name in PAGES_BLOCKED:
                return self.deny(request)
        return self.get_response(request)

    @staticmethod
    def deny(request):
        if _wants_json(request):
            return JsonResponse({"detail": DENY_MESSAGE}, status=403)
        return render(request, "readonly_denied.html", {"message": DENY_MESSAGE}, status=403)


def readonly_context(request):
    """Context processor: IS_READONLY nei template."""
    return {"IS_READONLY": is_readonly(getattr(request, "user", None))}
