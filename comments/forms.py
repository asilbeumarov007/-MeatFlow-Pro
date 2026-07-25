from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('comment',) # Faqat matn maydoni foydalanuvchiga ko'rinsin
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Fikringizni yozing...',
                'rows': 3
            }),
        }