# comments/models.py
from django.db import models
from django.conf import settings
from articles.models import Product # Article o'rniga Product import qilindi 🚀

class Comment(models.Model):
    # Maydon nomi product ga o'zgartirildi
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField(max_length=250)
    date_posted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} izohi"