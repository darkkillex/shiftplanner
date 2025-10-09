from pathlib import Path
import os, re
from functools import lru_cache

@lru_cache(maxsize=1)
def get_app_version() -> str:
    # Fallback immediato da ENV (utile in prod)
    env_ver = os.getenv("APP_VERSION")
    if env_ver:
        return env_ver

    # Candidati comuni
    candidates = []
    try:
        from django.conf import settings
        if getattr(settings, "BASE_DIR", None):
            candidates.append(Path(settings.BASE_DIR) / "CHANGELOG.md")          # ./CHANGELOG.md
            candidates.append(Path(settings.BASE_DIR).parent / "CHANGELOG.md")   # ../CHANGELOG.md
    except Exception:
        pass

    candidates += [
        Path("/app/CHANGELOG.md"),                          # tipico in Docker
        Path(__file__).resolve().parents[2] / "CHANGELOG.md",
        Path(__file__).resolve().parents[1] / "CHANGELOG.md",
        Path.cwd() / "CHANGELOG.md",
    ]

    path = next((p for p in candidates if p.exists()), None)
    if not path:
        return "v0.0.0"

    with path.open(encoding="utf-8") as f:
        for line in f:
            m = re.match(r"#\s*(v\d+\.\d+\.\d+)", line.strip())
            if m:
                return m.group(1)
    return "v0.0.0"
