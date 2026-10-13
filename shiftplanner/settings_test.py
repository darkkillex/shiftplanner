"""
Impostazioni per i test automatici:
    python manage.py test reports --settings=shiftplanner.settings_test

Le migrazioni di 'core' nel repository non sono allineate ai modelli
(mancano PlanRow, TemplateRow, Reminder, ...), quindi per i test lo schema
viene creato direttamente dai modelli invece che dalle migrazioni.
"""
from .settings import *  # noqa: F401,F403


class _NoMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _NoMigrations()
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STATICFILES_DIRS = []
