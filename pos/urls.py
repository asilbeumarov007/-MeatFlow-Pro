from django.urls import path
from . import views_api
from . import views

urlpatterns = [
    # Main POS Pages
    path('', views.terminal_view, name='terminal_root'),
    path('terminal/', views.terminal_view, name='terminal'),
    path('search-customers/', views.search_customers, name='search_customers'),
    path('save-sale/', views.save_sale, name='save_sale'),
    path('quick-customer/', views.quick_create_customer, name='quick_customer'),
    path('customer/update/<int:customer_id>/', views.update_customer, name='update_customer'),
    path('customers/', views.customers_view, name='customers'),
    path('daily-report/', views.daily_report_view, name='daily_report'),
    path('global-report/', views.global_analytics, name='global_analytics'),
    path('export-analytics-excel/', views.export_analytics_excel, name='export_analytics_excel'),
    path('export-slaughters-excel/', views.export_slaughters_excel, name='export_slaughters_excel'),
    path('debt-payment/', views.debt_payment_view, name='debt_payment'),
    path('api/process-debt-payment/', views.process_debt_payment, name='process_debt_payment'),
    path('cash-flow/', views.cash_flow_view, name='cash_flow'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant_page'),
    path('api/process-cash-transaction/', views.process_cash_transaction, name='process_cash_transaction'),
    path('debt-migration/', views.debt_migration_page, name='debt-migration'),
    path('api/save-migrated-debt/', views.save_migrated_debt, name='save_migrated_debt'),
    path('api/create-notebook/', views.create_notebook, name='create_notebook'),
    path('api/get-notebook-customers/<int:notebook_id>/', views.get_notebook_customers, name='get_notebook_customers'),
    path('notebooks/delete/<int:notebook_id>/', views.delete_notebook_view, name='delete_notebook'),
    path('yield-loss/', views.yield_loss_view, name='yield_loss'),
    path('api/process-slaughter/', views.process_slaughter_api, name='process_slaughter_api'),
    
    # Scale ESP8266/Kabel APIs
    path('api/receive-weight/', views.receive_weight_from_esp, name='receive_weight'),
    path('api/get-weight/', views.get_current_weight, name='get_weight'),
    path('api/tarozi/vazn/', views.get_current_weight, name='tarozi_vazn'),
    path('api/tarozi/yangila/', views.receive_weight_from_esp, name='tarozi_yangila'),
    path('api/sync-bootstrap/', views.sync_bootstrap, name='sync_bootstrap'),
    
    # Chat / Community
    path('chats/', views.customer_chats_dashboard, name='customer_chats_dashboard'),
    path('customer-chat/<int:customer_id>/', views.get_customer_chat_logs, name='customer_chat_logs'),
    path('customer-chat/send/<int:customer_id>/', views.send_chat_message, name='send_chat_message'),
    path('my-cabinet/', views.customer_profile_cabinet, name='customer_profile_cabinet'),
    path('api/my-chat/', views.customer_chat_api, name='customer_chat_api'),
    path('api/upload-payment-proof/', views.upload_payment_proof, name='upload_payment_proof'),
    path('api/export-my-logs/', views.export_customer_logs_excel, name='export_customer_logs'),
    path('api/ai-meat-assistant/', views.ai_meat_assistant_api, name='ai_meat_assistant_api'),
    
    # B2B Order Management
    path('api/b2b-orders/create/', views.create_b2b_order, name='create_b2b_order'),
    path('api/b2b-orders/update/<int:order_id>/', views.update_b2b_order_status, name='update_b2b_order_status'),
    path('api/b2b-orders/customer/<int:customer_id>/', views.get_customer_b2b_orders, name='get_customer_b2b_orders'),
    path('api/b2b-orders/pending-count/', views.get_pending_b2b_orders_count, name='pending_b2b_orders_count'),
    path('api/b2b-orders/create-ai-draft/', views.create_ai_draft_order, name='create_ai_draft_order'),

    # Kassa Shifti (Z-Report)
    path('api/shift/status/', views.get_current_shift_status, name='shift_status'),
    path('api/shift/open/', views.open_shift, name='shift_open'),
    path('api/shift/close/', views.close_shift, name='shift_close'),

    # Ta'minotchilar Boshqaruvi
    path('suppliers/', views.suppliers_view, name='suppliers_dashboard'),
    path('api/supplier/create/', views.process_supplier_create_api, name='supplier_create_api'),
    path('api/supplier/payment/', views.process_supplier_payment_api, name='supplier_payment_api'),
    path('api/supplier/ledger/<int:supplier_id>/', views.get_supplier_ledger_api, name='supplier_ledger_api'),
    path('api/supplier/export/<int:supplier_id>/', views.export_supplier_ledger_excel, name='export_supplier_ledger_excel'),

    # Utility
    path('switch-script/<str:script_mode>/', views.switch_script_view, name='switch_script'),

    # REST API Endpoints
    path('api/products/', views_api.api_products, name='api_products'),
    path('api/customers/', views_api.api_customers, name='api_customers'),
    path('api/suppliers/', views_api.api_suppliers, name='api_suppliers'),
    path('api/slaughters/create/', views_api.api_slaughters_create, name='api_slaughters_create'),
    path('api/sales/create/', views_api.api_sales_create, name='api_sales_create'),
    path('api/debts/migrate/', views_api.api_debts_migrate, name='api_debts_migrate'),
    path('api/debts/pay/', views_api.api_debts_pay, name='api_debts_pay'),
    path('api/reports/daily/', views_api.api_reports_daily, name='api_reports_daily'),
    path('api/reports/debt-aging/', views_api.api_reports_debt_aging, name='api_reports_debt_aging'),
    path('api/reports/yield-decay/', views_api.api_yield_decay_report, name='api_reports_yield_decay'),
    path('api/ai/copilot/', views_api.api_ai_copilot, name='api_ai_copilot'),
    path('api/notifications/', views_api.api_notifications, name='api_notifications'),
    path('api/customer/online-payment/', views.process_customer_online_payment, name='customer_online_payment'),
    path('api/ai/clear-history/', views.clear_ai_chat_history, name='clear_ai_history'),
    path('slaughter/report/<int:slaughter_id>/', views.slaughter_report_view, name='slaughter_report'),
    path('batch/report/<int:batch_id>/', views.batch_report_view, name='batch_report'),
    path('api/telegram/customer-bot/webhook/', views_api.customer_bot_webhook, name='customer_bot_webhook'),
    path('api/b2b-orders/create-with-proof/', views_api.api_b2b_create_with_proof, name='api_b2b_create_with_proof'),
    path('api/b2b-orders/live-tracking/<int:customer_id>/', views_api.api_b2b_live_tracking, name='api_b2b_live_tracking'),
    path('api/payment-settings/', views_api.api_payment_settings, name='api_payment_settings'),
    path('api/calculate-delivery/', views_api.api_calculate_delivery, name='api_calculate_delivery'),
    path('api/courier/apply/', views_api.api_courier_apply, name='api_courier_apply'),
    path('api/courier/orders/', views_api.api_courier_orders, name='api_courier_orders'),
    path('api/courier/accept-order/', views_api.api_courier_accept_order, name='api_courier_accept_order'),
    path('api/courier/complete-order/', views_api.api_courier_complete_order, name='api_courier_complete_order'),
]
