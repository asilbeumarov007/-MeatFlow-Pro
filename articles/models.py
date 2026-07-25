from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from ckeditor.fields import RichTextField

class Product(models.Model):
    ANIMAL_CHOICES = [
        ('Mol', "Mol go'shti"),
        ('Qo\'y', "Qo'y go'shti"),
        ('Tovuq', "Tovuq go'shti"),
        ('Boshqa', "Boshqa mahsulotlar"),
    ]

    name = models.CharField(max_length=200, verbose_name="Mahsulot nomi")
    animal_type = models.CharField(max_length=50, choices=ANIMAL_CHOICES, default='Mol', verbose_name="Hayvon turi")
    cut_type = models.CharField(max_length=100, verbose_name="Go'sht bo'lagi (Laxm, Qovurg'a, To'sh va h.k.)")
    price = models.IntegerField(verbose_name="Narxi (1 kg uchun so'mda)")
    stock_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Ombordagi qoldiq (kg)")
    description = RichTextField(null=True, blank=True, verbose_name="Mahsulot ta'rifi")
    photo = models.ImageField(upload_to='products/', blank=True, verbose_name="Asosiy rasm")
    date = models.DateField(auto_now_add=True, null=True)
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Mas'ul xodim"
    )

    def __str__(self):
        return f"{self.name} ({self.animal_type})"

    @property
    def title(self):
        return self.name

    @property
    def summary(self):
        import re
        if self.description:
            clean = re.sub('<[^<]+?>', '', self.description)
            return clean
        return ""

    def get_absolute_url(self):
        return reverse('article_detail', kwargs={'pk': self.pk})

class ProductImage(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')

    def __str__(self):
        return f"{self.product.name} qo'shimcha rasmi"