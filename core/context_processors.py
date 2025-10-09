from core.utils.versioning import get_app_version

def app_version(request):
    """
    Aggiunge 'APP_VERSION' al contesto di tutti i template
    """
    return {'APP_VERSION': get_app_version()}
