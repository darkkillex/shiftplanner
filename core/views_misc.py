from django.shortcuts import render
from django.conf import settings
from pathlib import Path

def changelog_view(request):
    # Percorsi candidati (coerenti con get_app_version)
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
