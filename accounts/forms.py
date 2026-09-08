from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=25,
        required=True,
        label="Telefon raqamingiz",
        help_text="Xaridlar, bonuslar va yetkazib berish uchun asosiy raqamingiz",
        widget=forms.TextInput(attrs={
            'placeholder': '+998 90 123 45 67',
            'class': 'form-control',
            'autocomplete': 'tel'
        })
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'phone', 'email')

    def clean_phone(self):
        raw = self.cleaned_data.get('phone', '').strip()
        clean = ''.join(c for c in raw if c.isdigit() or c == '+')
        if not clean.startswith('+'):
            if clean.startswith('998'):
                clean = '+' + clean
            else:
                clean = '+998' + clean
        
        digits = ''.join(filter(str.isdigit, clean))
        if len(digits) != 12:  # 998 + 9 raqam
            raise forms.ValidationError("Telefon raqami to'liq kiritilishi kerak (masalan: +998 90 123 45 67)")
        
        return f"+{digits}"

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'age',)