import random
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib import messages
from .forms import CustomUserCreationForm

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        phone = form.cleaned_data.get('phone')

        if not user.email:
            user.email = phone
            user.save(update_fields=['email'])

        from pos.models import Customer, CustomerLog
        welcome_bonus = 5

        customer = Customer.objects.filter(phone=phone).first()

        if customer:
            if not customer.first_name and user.first_name:
                customer.first_name = user.first_name
            if not customer.last_name and user.last_name:
                customer.last_name = user.last_name
            if "Saytdan" not in (customer.note or ''):
                customer.note = f"{customer.note or ''} | 🌐 Sayt: @{user.username}".strip(' |')
            customer.save()
            messages.success(
                self.request,
                f"Xush kelibsiz, {customer.first_name}! Sizning do'kondagi mijoz kartangiz (ID: {customer.custom_id}) yangi profilingizga bog'landi. Endi tizimga kirishingiz mumkin."
            )
        else:
            custom_id = f"C-{random.randint(1000, 9999)}"
            while Customer.objects.filter(custom_id=custom_id).exists():
                custom_id = f"C-{random.randint(1000, 9999)}"

            customer = Customer.objects.create(
                first_name=user.first_name or user.username,
                last_name=user.last_name or '',
                phone=phone,
                custom_id=custom_id,
                bonus_points=welcome_bonus,
                note=f"🌐 Saytdan mustaqil ro'yxatdan o'tgan mijoz (@{user.username})"
            )

            CustomerLog.objects.create(
                customer=customer,
                log_type='bonus',
                title="🎁 Xush kelibsiz bonusi!",
                amount=welcome_bonus,
                note=f"Baxmal Meat tizimidan mustaqil ro'yxatdan o'tganingiz uchun {welcome_bonus} bonus balli sovg'a qilindi!"
            )

            messages.success(
                self.request,
                f"Tabriklaymiz, {customer.first_name}! Hisobingiz yaratildi va sizga {welcome_bonus} start bonus balli sovg'a qilindi. Endi tizimga kirishingiz mumkin!"
            )

        # Notify Admin Telegram Bot
        try:
            from pos.views_api import send_telegram_notification
            send_telegram_notification(
                f"🆕 *Yangi Mijoz Saytdan Ro'yxatdan O'tdi!*\n\n"
                f"👤 *F.I.O:* {customer.first_name} {customer.last_name or ''}\n"
                f"📞 *Telefon:* `{customer.phone}`\n"
                f"🆔 *Mijoz ID:* `{customer.custom_id}`\n"
                f"⭐ *Start Bonus:* `{welcome_bonus}` ball\n"
                f"🌐 *Akkaunt:* @{user.username}"
            )
        except Exception as e:
            pass

        return response