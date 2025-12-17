from core.utils.versioning import get_app_version
from django.conf import settings

def app_version(request):
    """
    Aggiunge 'APP_VERSION' al contesto di tutti i template
    """
    return {'APP_VERSION': get_app_version()}

def company_context(request):
    return {
        "COMPANY_NAME": settings.COMPANY_NAME
    }