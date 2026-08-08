from .models import StoreSetting

def store_settings(request):
    store = StoreSetting.objects.filter(is_active=True).first()
    return {'store': store}
