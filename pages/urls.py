from django.urls import path
from django.shortcuts import redirect
from .views import HomePageView

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('customers/', lambda req: redirect('customers')),
    path('ai/', lambda req: redirect('ai_assistant_page')),
    path('ai-assistant/', lambda req: redirect('ai_assistant_page')),
    path('terminal/', lambda req: redirect('terminal')),
]