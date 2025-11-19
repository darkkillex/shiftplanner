from django.shortcuts import render
from django.conf import settings
from pathlib import Path

def changelog_view(request):
    """
    Mostra il file Markdown del changelog.
    """
    candidates = [
        Path(getattr(settings, "BASE_DIR", Path("/app"))) / "CHANGELOG.md",
        Path("/app/CHANGELOG.md"),
    ]
    path = next((p for p in candidates if p.exists()), None)

    raw = ""
    if path:
        raw = path.read_text(encoding="utf-8")

    # Prova a renderizzare come Markdown se disponibile
    html = ""
    try:
        import markdown
        html = markdown.markdown(raw, extensions=["fenced_code", "tables"])
    except Exception:
        # fallback: testo preformattato
        html = f"<pre style='white-space:pre-wrap'>{raw}</pre>"

    return render(request, "changelog.html", {"html": html})



def user_manual_view(request):
    """
    Mostra il file Markdown della documentazione utente.
    """
    candidates = [
        Path(getattr(settings, "BASE_DIR", Path("/app"))) / "docs" / "SHIFTPLANNER_DOC_UTENTE.md",
        Path("/app/docs/SHIFTPLANNER_DOC_UTENTE.md"),
    ]
    path = next((p for p in candidates if p.exists()), None)

    raw = ""
    if path:
        raw = path.read_text(encoding="utf-8")

    # Prova a convertire il Markdown
    html = ""
    try:
        import markdown
        html = markdown.markdown(raw, extensions=["fenced_code", "tables"])
    except Exception:
        html = f"<pre style='white-space:pre-wrap'>{raw}</pre>"

    return render(request, "doc_user.html", {"html": html})