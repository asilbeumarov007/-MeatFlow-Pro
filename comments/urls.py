# comments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Manzil do'kon uslubiga moslandi, funksiya nomi esa o'z joyida 🚀
    path('product-reviews/<int:pk>/', views.post_detail, name='post_detail'),
]