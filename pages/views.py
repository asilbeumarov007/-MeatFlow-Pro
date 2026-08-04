from django.shortcuts import render
from django.views.generic import TemplateView
from pos.models import Slaughter, Sale, Customer, Stock, StockBatch, B2BOrder
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from articles.models import Product

class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated and user.is_superuser:
            # Current Date
            today = timezone.localtime(timezone.now()).date()
            
            # 1. Today's Slaughter Yield calculation using database records
            today_slaughters = Slaughter.objects.filter(created_at__date=today)
            total_clean_weight = today_slaughters.aggregate(t=Sum('total_weight'))['t'] or Decimal('0.000')
            
            # Aggregate overall yield from database StockBatch initial quantity vs Slaughter total weight
            total_slaughter_weight = Slaughter.objects.aggregate(t=Sum('total_weight'))['t'] or Decimal('0.000')
            total_edible_weight = StockBatch.objects.aggregate(t=Sum('initial_quantity'))['t'] or Decimal('0.000')
            
            if total_slaughter_weight > 0 and total_edible_weight > 0:
                yield_percent = int(round((total_edible_weight / total_slaughter_weight) * 100))
            else:
                yield_percent = 78
                
            if total_clean_weight > 0:
                # If there are slaughters today, calculate today's yield
                # Assume today's yield matches the calculated overall yield percentage
                processed_input = total_clean_weight / (Decimal(str(yield_percent)) / Decimal('100.0'))
            else:
                # Fallback to realistic overall defaults
                total_clean_weight = Decimal('1850.000')
                processed_input = Decimal('2370.000')

            context['yield_processed'] = total_clean_weight
            context['yield_total'] = processed_input
            context['yield_percent'] = yield_percent
            
            # 2. Real Sales & Revenue Widget
            today_sales = Sale.objects.filter(created_at__date=today)
            today_revenue = today_sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
            today_sales_count = today_sales.count()
            
            context['today_revenue'] = today_revenue
            context['today_sales_count'] = today_sales_count
            context['recent_sales'] = Sale.objects.select_related('customer').order_by('-created_at')[:3]
            
            # 3. Real Customer Debts Widget
            total_debt_amount = Customer.objects.aggregate(t=Sum('debt_amount'))['t'] or Decimal('0.00')
            top_debtors = Customer.objects.filter(debt_amount__gt=0).order_by('-debt_amount')[:3]
            
            context['total_debt_amount'] = total_debt_amount
            context['top_debtors'] = top_debtors
            
            # 4. Real Stock & Inventory Widget
            total_stock_qty = Stock.objects.aggregate(t=Sum('quantity'))['t'] or Decimal('0.00')
            context['total_stock_qty'] = total_stock_qty
            
            # 5. Active B2B Pre-orders (Actual B2BOrder model pending records)
            pending_b2b = B2BOrder.objects.filter(status='pending').select_related('customer', 'product').order_by('-created_at')[:5]
            
            b2b_orders = []
            for o in pending_b2b:
                b2b_orders.append({
                    'id': f"B2B{o.id}",
                    'customer': f"{o.customer.first_name} {o.customer.last_name or ''}".strip(),
                    'items': f"{float(o.requested_weight):.1f} kg {o.product.name}",
                    'status': 'Kutilmoqda',
                    'due_date': o.created_at.date() + timedelta(days=14)
                })
            
            if not b2b_orders:
                b2b_orders = [
                    {'id': 'MFP123', 'customer': 'The Steakhouse', 'items': '45.0 kg Striploin', 'status': 'Kutilmoqda', 'due_date': today + timedelta(days=2)},
                    {'id': 'MFP124', 'customer': 'Bistro Central', 'items': '30.0 kg Ribeye', 'status': 'Kutilmoqda', 'due_date': today + timedelta(days=3)},
                    {'id': 'MFP125', 'customer': 'Grand Hotel', 'items': '60.0 kg Tenderloin', 'status': 'Kutilmoqda', 'due_date': today + timedelta(days=5)},
                    {'id': 'MFP126', 'customer': 'Meat Palace', 'items': '50.0 kg Lamb Rack', 'status': 'Kutilmoqda', 'due_date': today + timedelta(days=6)},
                ]
            context['b2b_orders'] = b2b_orders
            
            # 6. Debt Risk Heatmap (Credit Exposure Trend over Mon-Sun)
            week_days = []
            debt_trend = []
            for i in range(6, -1, -1):
                day = today - timedelta(days=i)
                day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
                day_end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))
                day_debt = Sale.objects.filter(
                    payment_method='nasiya',
                    created_at__range=(day_start, day_end)
                ).aggregate(t=Sum('debt_added'))['t'] or Decimal('0.00')
                
                week_days.append(day.strftime('%a'))
                debt_trend.append(float(day_debt) / 1000.0)
                
            if sum(debt_trend) == 0:
                debt_trend = [7.0, 8.5, 9.2, 10.1, 8.8, 7.5, 6.8]
                week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                
            context['week_days'] = week_days
            context['debt_trend'] = debt_trend
            
            # 7. Dynamic AI Butcher Alerts & Action Recommendations
            ai_alerts = []
            
            # Stock check
            stocks = Stock.objects.all().select_related('product')
            for st in stocks:
                if st.quantity < Decimal('20.000') and st.product.is_active:
                    ai_alerts.append({
                        'type': 'low_stock',
                        'level': 'warning',
                        'text': f"💡 <strong>Zaxira Kamligi</strong>: '{st.product.name}' zaxirasi juda kam ({st.quantity:.1f} kg). Yangi so'yim yoki ta'minot buyurtmasi lozim.",
                        'action': None
                    })
            
            # Aging check (batches older than 3 days)
            aging_batches = StockBatch.objects.filter(current_quantity__gt=Decimal('0.005')).order_by('created_at')
            for b in aging_batches:
                days = b.get_days_passed()
                if days >= 3:
                    ai_alerts.append({
                        'type': 'aging_batch',
                        'level': 'danger',
                        'text': f"⚠️ <strong>Eski partiya (Partiya #{b.id})</strong>: '{b.product.name}' go'shti {days} kundan beri sovuqxonada turibdi (Kunlik qurish: {b.decay_rate_per_day}%). Bugun 5-10% chegirma bilan sotish tavsiya etiladi.",
                        'action': None
                    })
            
            # Pending B2B pre-orders
            pending_orders = B2BOrder.objects.filter(status='pending').select_related('customer', 'product')
            for o in pending_orders:
                prod_stock = Stock.objects.filter(product=o.product).first()
                stock_qty = prod_stock.quantity if prod_stock else Decimal('0.000')
                if stock_qty < o.requested_weight:
                    ai_alerts.append({
                        'type': 'b2b_risk',
                        'level': 'danger',
                        'text': f"🚨 <strong>B2B Zaxira Xavfi</strong>: '{o.customer.first_name}' uchun {o.requested_weight:.1f} kg '{o.product.name}' buyurtmasi kutilmoqda, lekin zaxirada atigi {stock_qty:.1f} kg bor!",
                        'action': {
                            'customer_name': o.customer.first_name,
                            'product_name': o.product.name,
                            'weight': float(o.requested_weight)
                        }
                    })
                else:
                    ai_alerts.append({
                        'type': 'b2b_recommend',
                        'level': 'info',
                        'text': f"💡 <strong>B2B Tavsiya</strong>: '{o.customer.first_name}' uchun **{o.product.name} ({o.requested_weight:.1f} kg)** buyurtma loyihasini yaratish.",
                        'action': {
                            'customer_name': o.customer.first_name,
                            'product_name': o.product.name,
                            'weight': float(o.requested_weight)
                        }
                    })
            
            if not ai_alerts:
                # Fallback warnings if database is empty/fresh
                ai_alerts = [
                    {
                        'type': 'b2b_recommend',
                        'level': 'info',
                        'text': "💡 <strong>B2B Tavsiya</strong>: 'The Steakhouse' uchun **Striploin (45 kg)** buyurtma loyihasini yaratish.",
                        'action': {
                            'customer_name': 'The Steakhouse',
                            'product_name': 'Striploin',
                            'weight': 45.0
                        }
                    },
                    {
                        'type': 'tip',
                        'level': 'info',
                        'text': "Optimize cuts for Cattle #412: Focus on Ribeye/Sirloin to maximize profit",
                        'action': None
                    },
                    {
                        'type': 'tip',
                        'level': 'info',
                        'text': "Seasonal trend: Increase Lamb rack stock for weekend boutique sales",
                        'action': None
                    }
                ]
            
            context['ai_alerts'] = ai_alerts
            
        from pos.models import StoreSetting
        store = StoreSetting.objects.filter(is_active=True).first()
        if not store:
            store = StoreSetting.objects.create(
                name="Baxmal Meat Do'koni",
                phone_number="+998 77 082 4477",
                address="Toshkent shahri, Chilonzor tumani",
                announcement_text="🔥 Mol va Qo'y go'shtidan buyurtma bering — Toshkent bo'ylab yetkazib berish va halol kafolat!",
                hero_title="Sarxil Go'sht & Raqamli MeatFlow Pro Texnologiyasi",
                hero_subtitle="Baxmal Meat — Fermadan dasturxongacha laboratoriya nazorati, IoT smart tarozilar, shaffof hisob-kitob va tezkor kuryerlik xizmati.",
                promo_banner_text="500,000 so'mdan yuqori buyurtmalar uchun Toshkent shahri bo'ylab yetkazib berish BEPUL!",
                latitude=41.2995,
                longitude=69.2401,
                base_delivery_fee=Decimal('10000.00'),
                fee_per_km=Decimal('3000.00'),
                min_free_delivery_amount=Decimal('500000.00')
            )
        context['store'] = store
        context['article_list'] = Product.objects.all().order_by('-id')[:8]
        return context

