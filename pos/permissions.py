from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import redirect

def is_staff_or_admin(user):
    """Foydalanuvchi tizimga kirgan va xodim (is_staff) yoki admin (is_superuser) ekanligini tekshiradi."""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def is_admin(user):
    """Foydalanuvchi faqat administrator (superuser) ekanligini tekshiradi."""
    return user.is_authenticated and user.is_superuser

def staff_required(view_func):
    """Oddiy kassir va administratorlar uchun ruxsat beruvchi dekorator."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/pos/api/'):
                return JsonResponse({
                    'status': 'error',
                    'message': "Kirish taqiqlangan! Kassir yoki Admin huquqi talab etiladi."
                }, status=403)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Faqat administratorlar (superuser) uchun ruxsat beruvchi dekorator."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/pos/api/'):
                return JsonResponse({
                    'status': 'error',
                    'message': "Kirish taqiqlangan! Faqat Administratorlar uchun."
                }, status=403)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
