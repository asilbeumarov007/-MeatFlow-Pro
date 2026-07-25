# comments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from articles.models import Product  # Yangi mahsulot modelimiz
from .models import Comment
from .forms import CommentForm


def post_detail(request, pk):
    # Eski Article o'rniga Product qidiriladi
    product = get_object_or_404(Product, pk=pk)

    # Izohlarni mahsulotga bog'langan holda olish
    comments = Comment.objects.filter(product__pk=product.pk).order_by('-date_posted')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.product = product  # To'g'ri bog'lash
            new_comment.author = request.user  # Muallifni biriktirish
            new_comment.save()
            return redirect('article_detail', pk=product.pk)
    else:
        form = CommentForm()

    return render(request, 'comments/post_detail.html', {
        'product': product,
        'comments': comments,
        'form': form,
    })