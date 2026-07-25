from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import json

from .models import Supplier, Product, Stock, Slaughter, Customer, Sale, SaleItem, CustomerLog

class POSAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="admin",
            password="adminpassword",
            email="admin@example.com"
        )
        self.client.login(username="admin", password="adminpassword")
        
        # Ta'minotchi yaratish
        self.supplier = Supplier.objects.create(
            first_name="Islom",
            last_name="Karimov",
            phone="+998901234567",
            custom_id="T-1234"
        )
        
        # Mahsulot yaratish
        self.beef = Product.objects.create(
            name="Mol go'shti",
            price_per_kg=Decimal('140000.00')
        )
        self.stock = Stock.objects.create(
            product=self.beef,
            quantity=Decimal('50.000')
        )
        
        # Mijoz yaratish
        self.customer = Customer.objects.create(
            first_name="Eshmat",
            last_name="Toshmatov",
            phone="+998937654321",
            custom_id="M-4321",
            bonus_points=1000,
            debt_amount=Decimal('0.00')
        )

    def test_api_products(self):
        response = self.client.get(reverse('api_products'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Mol go'shti")
        self.assertEqual(data[0]['stock'], 50.0)

    def test_api_customers_search_and_create(self):
        # 1. Qidiruv test
        response = self.client.get(reverse('api_customers') + "?q=Eshmat")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['phone'], "+998937654321")

        # 2. Yangi mijoz yaratish test
        new_customer_data = {
            "first_name": "Toshmat",
            "last_name": "Eshmatov",
            "phone": "+998991234567",
            "note": "Doimiy xaridor"
        }
        response = self.client.post(
            reverse('api_customers'),
            data=json.dumps(new_customer_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertIn('custom_id', res_data)
        self.assertEqual(res_data['phone'], "+998991234567")

    def test_api_slaughters_create(self):
        slaughter_data = {
            "supplier_id": self.supplier.id,
            "animal_type": "mol",
            "total_weight": 150.5,
            "purchase_price": 125000,
            "due_days": 14
        }
        response = self.client.post(
            reverse('api_slaughters_create'),
            data=json.dumps(slaughter_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(float(res_data['total_cost']), 150.5 * 125000)
        
        # Zaxira va ta'minotchi qarzini tekshiramiz
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.our_debt, Decimal(str(150.5 * 125000)))
        
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal('200.500')) # 50 + 150.5

    def test_api_slaughters_create_for_customer(self):
        self.customer.debt_amount = Decimal('500000.00')
        self.customer.save()
        
        slaughter_data = {
            "supplier_id": f"customer_{self.customer.id}",
            "animal_type": "qoy",
            "total_weight": 5.000,
            "purchase_price": 80000,
            "due_days": 7
        }
        response = self.client.post(
            reverse('api_slaughters_create'),
            data=json.dumps(slaughter_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(float(res_data['total_cost']), 400000.0)
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.debt_amount, Decimal('100000.00'))
        
        logs = CustomerLog.objects.filter(customer=self.customer, log_type='debt_pay')
        self.assertTrue(logs.exists())
        self.assertIn("Go'sht sotib olindi", logs.first().title)

    def test_api_sales_create_with_discount_and_bonus(self):
        sale_data = {
            "customer_id": self.customer.id,
            "payment_method": "naqd",
            "items": [
                {"product_id": self.beef.id, "weight": 2.500} # 2.5 * 140k = 350,000 so'm
            ],
            "total_amount": 350000,
            "discount_amount": 5000, # Kassir o'tib bergan chegirma
            "bonus_used": 1000, # 1,000 so'm bonusdan to'landi
            "debt_added": 0,
            "final_paid": 344000 # Mijoz to'lagan naqd pul
        }
        response = self.client.post(
            reverse('api_sales_create'),
            data=json.dumps(sale_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Mijoz bonuslarini tekshirish (1000 bonus ishlatildi, 344k sotuvdan 1% = 3440 bonus yig'ildi)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.bonus_points, 3440) # 1000 - 1000 + 3440
        self.assertEqual(self.customer.debt_amount, Decimal('0.00'))

        # Zaxira tekshiruvi (50kg edi - 2.5kg = 47.5kg)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, Decimal('47.500'))

        # Sale logs va CustomerLog tekshiruvi
        logs = CustomerLog.objects.filter(customer=self.customer, log_type='sale')
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs[0].amount, Decimal('344000.00'))

    def test_api_sales_create_with_nasiya(self):
        sale_data = {
            "customer_id": self.customer.id,
            "payment_method": "nasiya",
            "items": [
                {"product_id": self.beef.id, "weight": 1.000} # 140,000 so'm
            ],
            "total_amount": 140000,
            "discount_amount": 0,
            "bonus_used": 0,
            "debt_added": 140000,
            "final_paid": 0
        }
        response = self.client.post(
            reverse('api_sales_create'),
            data=json.dumps(sale_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Mijoz qarzini tekshirish
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.debt_amount, Decimal('140000.00'))

    def test_api_debts_migrate(self):
        migrate_data = {
            "entries": [
                {"name": "Daftardagi Xaridor", "phone": "+998941234567", "amount": 250000, "direction": "client"},
                {"name": "Daftardagi Ta'minotchi", "phone": "+998951234567", "amount": 500000, "direction": "supplier"}
            ]
        }
        response = self.client.post(
            reverse('api_debts_migrate'),
            data=json.dumps(migrate_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Mijoz va ta'minotchi qarzlarini tekshiramiz
        migrated_client = Customer.objects.get(phone="+998941234567")
        self.assertEqual(migrated_client.debt_amount, Decimal('250000.00'))

        migrated_supplier = Supplier.objects.get(phone="+998951234567")
        self.assertEqual(migrated_supplier.our_debt, Decimal('500000.00'))

    def test_yield_decay_and_batches(self):
        # 1. Create a slaughter batch
        slaughter_data = {
            "supplier_id": self.supplier.id,
            "animal_type": "mol",
            "total_weight": 100.0,
            "purchase_price": 100000,
            "due_days": 10
        }
        response = self.client.post(
            reverse('api_slaughters_create'),
            data=json.dumps(slaughter_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Verify batch was created
        from .models import StockBatch
        batches = StockBatch.objects.filter(product__name="Mol go'shti")
        self.assertEqual(batches.count(), 1)
        batch = batches.first()
        self.assertEqual(batch.initial_quantity, Decimal('100.000'))

        # Check decay weight (0 days passed should show no loss)
        self.assertEqual(batch.get_decayed_weight(), Decimal('100.000'))
        self.assertEqual(batch.get_decay_loss(), Decimal('0.000'))
        self.assertEqual(batch.get_real_cost_per_kg(), Decimal('100000.00'))

        # Simulate 2 days hanging by changing created_at back
        import datetime
        from django.utils import timezone
        batch.created_at = timezone.now() - datetime.timedelta(days=2)
        batch.save()

        # Decay is 1% per day: 100 * (0.99)^2 = 98.01 kg
        self.assertEqual(batch.get_decayed_weight(), Decimal('98.010'))
        self.assertEqual(batch.get_decay_loss(), Decimal('1.990'))
        self.assertEqual(batch.get_real_cost_per_kg(), Decimal('102030.41')) # 10,000,000 / 98.01

        # 2. Make a sale of 10kg. It should deduct from the batch current_quantity (100 -> 90)
        sale_data = {
            "customer_id": self.customer.id,
            "payment_method": "naqd",
            "items": [
                {"product_id": self.beef.id, "weight": 10.000}
            ],
            "total_amount": 1400000,
            "discount_amount": 0,
            "bonus_used": 0,
            "debt_added": 0,
            "final_paid": 1400000
        }
        response = self.client.post(
            reverse('api_sales_create'),
            data=json.dumps(sale_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        batch.refresh_from_db()
        self.assertEqual(batch.current_quantity, Decimal('90.000'))

        # 3. Call reports yield decay API and check response
        response = self.client.get(reverse('api_reports_yield_decay'))
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(len(res_data['batches']), 1)
        self.assertIn('summary', res_data)
        self.assertGreater(res_data['summary']['total_loss_kg'], 0)

    def test_global_analytics_and_excel(self):
        # 1. Login as superuser
        self.client.force_login(self.admin_user)

        # 2. Get global analytics page
        response = self.client.get(reverse('global_analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('grouped_sales', response.context)
        self.assertIn('jami_kirim', response.context)

        # 3. Apply search query filters
        response = self.client.get(
            reverse('global_analytics'),
            {'search_query': 'Mijoz', 'payment_method': 'naqd'}
        )
        self.assertEqual(response.status_code, 200)

        # 4. Get excel export
        response = self.client.get(
            reverse('export_analytics_excel'),
            {'search_query': 'Mijoz', 'payment_method': 'naqd'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/ms-excel')

    def test_b2b_orders_workflow(self):
        # 1. Login as the customer's corresponding user account.
        # Eshmat's phone number is +998937654321, let's create a customer user.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        customer_user = User.objects.create_user(
            username="+998937654321",
            password="custpassword",
            email="+998937654321"
        )
        self.client.login(username="+998937654321", password="custpassword")

        # 2. Create B2B Order
        order_payload = {
            "product_name": "Mol go'shti",
            "weight": "15.5",
            "notes": "Premium quality beef, lean cut"
        }
        response = self.client.post(
            reverse('create_b2b_order'),
            data=json.dumps(order_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = json.loads(response.content)
        self.assertEqual(res_data['status'], 'success')
        self.assertIn('order_id', res_data)

        # Verify B2BOrder and CustomerLog exist
        from pos.models import B2BOrder, CustomerLog
        order = B2BOrder.objects.get(id=res_data['order_id'])
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.product, self.beef)
        self.assertEqual(order.requested_weight, Decimal('15.50'))
        self.assertEqual(order.status, 'pending')

        log = CustomerLog.objects.filter(customer=self.customer, title="Mijoz xabari").first()
        self.assertIsNotNone(log)
        self.assertIn("B2B BUYURTMA", log.message)

        # 3. Retrieve customer orders (login back as admin/superuser)
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('get_customer_b2b_orders', args=[self.customer.id]))
        self.assertEqual(response.status_code, 200)
        orders_list = json.loads(response.content)
        self.assertEqual(len(orders_list), 1)
        self.assertEqual(orders_list[0]['product_name'], "Mol go'shti")
        self.assertEqual(orders_list[0]['status'], 'pending')

        # 4. Verify pending count before update (should be 1 because it's pending)
        response = self.client.get(reverse('pending_b2b_orders_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['count'], 1)

        # 5. Update B2B Order status
        response = self.client.post(
            reverse('update_b2b_order_status', args=[order.id]),
            data=json.dumps({"status": "approved"}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'approved')

        # Verify pending count after update (should be 0 because it's approved)
        response = self.client.get(reverse('pending_b2b_orders_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['count'], 0)

        # Verify notice posted to logs
        log_notice = CustomerLog.objects.filter(customer=self.customer, title="Do'kon xabari").first()
        self.assertIsNotNone(log_notice)
        self.assertIn("Sizning B2B buyurtmangiz", log_notice.message)
        self.assertIn("Tasdiqlandi", log_notice.message)
