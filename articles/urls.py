from django.urls import path
from .views import (
    ProductListView,
    ProductUpdateView,
    ProductDeleteView,
    ProductCreateView,
    product_detail,
)

urlpatterns = [
    # Yo'llar o'sha-o'sha turadi, faqat name='...' qismi eski holiga qaytadi 🚀
    path('<int:pk>/', product_detail, name='article_detail'),
    path('<int:pk>/edit/', ProductUpdateView.as_view(), name='article_edit'),
    path('<int:pk>/delete/', ProductDeleteView.as_view(), name='article_delete'),
    path('new/', ProductCreateView.as_view(), name='article_new'),
    path('', ProductListView.as_view(), name='article_list'),
]