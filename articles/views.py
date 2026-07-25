# articles/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView
from django.views.generic.edit import UpdateView, DeleteView, CreateView
from django.urls import reverse_lazy
from .models import Product
from comments.forms import CommentForm
from django.contrib.auth.decorators import login_required
from .forms import ProductImageFormSet

# Ro'yxat ko'rinishi
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'article_list.html'
    context_object_name = 'article_list'  # Shablon eski nom bilan o'qishi uchun 🚀

# MAHSULOT DETALI VA IZOHLAR
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    comments = product.comments.all().order_by('-date_posted') if hasattr(product, 'comments') else []

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.product = product
            new_comment.author = request.user
            new_comment.save()
            return redirect('article_detail', pk=product.pk)
    else:
        form = CommentForm()

    return render(request, 'article_detail.html', {
        'article': product,  # 'product' o'rniga 'article' deb uzatamiz, shablon xato bermasligi uchun 🚀
        'comments': comments,
        'form': form
    })

# Tahrirlash
class ProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    template_name = 'article_edit.html'
    fields = ('name', 'animal_type', 'cut_type', 'price', 'stock_kg', 'description', 'photo')
    context_object_name = 'article'  # Shablon ichidagi o'zgaruvchi nomi uchun 🚀

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['images'] = ProductImageFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            data['images'] = ProductImageFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        images = context['images']
        if images.is_valid():
            self.object = form.save()
            images.instance = self.object
            images.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def test_func(self):
        return self.request.user.is_superuser

# O'chirish
class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Product
    template_name = 'article_delete.html'
    success_url = reverse_lazy('article_list')
    context_object_name = 'article'  # Shablon ichidagi o'zgaruvchi nomi uchun 🚀

    def test_func(self):
        return self.request.user.is_superuser

# Yangi mahsulot yaratish
class ProductCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Product
    template_name = 'article_new.html'
    fields = ('name', 'animal_type', 'cut_type', 'price', 'stock_kg', 'description', 'photo')
    context_object_name = 'article'  # Shablon ichidagi o'zgaruvchi nomi uchun 🚀

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        return self.request.user.is_superuser