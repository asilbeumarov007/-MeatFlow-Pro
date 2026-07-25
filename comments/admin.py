# comments/admin.py
from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    # 'article' o'rniga 'product' yozildi 🚀
    list_display = ['author', 'product', 'date_posted']