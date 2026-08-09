# -*- coding: utf-8 -*-
import sys

new_base_html = '''{% load static %}
<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}MeatFlow Pro | Baxmal Meat Boutique{% endblock %}</title>
  
  <!-- Favicon -->
  <link rel="icon" type="image/jpeg" href="{% static 'images/meatflow_logo.jpg' %}">
  
  <!-- Bootstrap 5 CSS & JS Bundle -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/bootstrap.bundle.min.js"></script>
  
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <style>
    :root {
      --primary: #1B6B4A;
      --primary-dark: #061E14;
      --accent: #D4A853;
      --text-main: #1A1A2E;
      --text-muted: #6B7280;
      --bg-light: #F4F6F5;
      --font-main: 'Plus Jakarta Sans', sans-serif;
      --font-serif: 'DM Serif Display', serif;
    }

    body {
      font-family: var(--font-main);
      background-color: var(--bg-light);
      color: var(--text-main);
      margin: 0;
      padding: 0;
    }

    /* ── EXECUTIVE ADMIN NAVBAR ── */
    .unified-header {
      background: linear-gradient(135deg, #051610 0%, #0A2B1E 60%, #061E14 100%);
      border-bottom: 1px solid rgba(212, 168, 83, 0.25);
      padding: 8px 24px;
      position: sticky;
      top: 0;
      z-index: 1050;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      backdrop-filter: blur(10px);
    }
    .header-container {
      max-width: 1440px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    /* Brand Logo */
    .header-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }
    .brand-logo-wrapper {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      padding: 2px;
      background: linear-gradient(135deg, #10B981, #059669);
      box-shadow: 0 4px 14px rgba(16,185,129,0.3);
    }
    .brand-logo-img {
      width: 100%;
      height: 100%;
      border-radius: 10px;
      object-fit: cover;
    }
    .brand-name {
      font-family: var(--font-main);
      font-size: 18px;
      font-weight: 800;
      color: #FFFFFF;
      letter-spacing: -0.3px;
      line-height: 1;
    }
    .brand-sub {
      font-size: 8.5px;
      color: var(--accent);
      letter-spacing: 1.2px;
      text-transform: uppercase;
      font-weight: 700;
      margin-top: 2px;
      display: block;
    }

    /* Admin Direct Nav Tabs */
    .header-links {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-wrap: wrap;
    }
    .header-link-item {
      color: rgba(255,255,255,0.85);
      text-decoration: none;
      font-size: 12.5px;
      font-weight: 600;
      padding: 6px 13px;
      border-radius: 50px;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }
    .header-link-item:hover {
      color: #FFFFFF !important;
      background: rgba(255,255,255,0.1);
    }
    .header-link-item.active {
      color: var(--accent) !important;
      background: rgba(255,255,255,0.15);
      font-weight: 700;
      box-shadow: inset 0 0 0 1px rgba(212,168,83,0.3);
    }

    .ai-link-item {
      color: #F59E0B !important;
      background: rgba(245,158,11,0.12) !important;
      border: 1px solid rgba(245,158,11,0.25);
    }
    .ai-link-item:hover {
      background: rgba(245,158,11,0.25) !important;
      color: #FFFFFF !important;
    }

    /* Script Switcher */
    .script-toggle-compact {
      display: inline-flex;
      background: rgba(255,255,255,0.08);
      border-radius: 30px;
      padding: 2px;
      border: 1px solid rgba(255,255,255,0.12);
    }
    .script-btn-compact {
      color: rgba(255,255,255,0.7);
      text-decoration: none;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 30px;
      transition: all 0.2s;
    }
    .script-btn-compact.active {
      background: #10B981;
      color: #FFFFFF !important;
      box-shadow: 0 2px 8px rgba(16,185,129,0.4);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .dropdown-menu.show {
      display: block !important;
      opacity: 1 !important;
      visibility: visible !important;
    }

    /* Mobile toggle */
    .mobile-toggle-btn {
      display: none;
      background: transparent;
      border: none;
      color: #FFFFFF;
      font-size: 24px;
      cursor: pointer;
    }

    /* Mobile menu */
    .mobile-menu-drawer {
      display: none;
      background: #061E14;
      border-top: 1px solid rgba(255,255,255,0.1);
      padding: 16px 24px;
    }

    @media (max-width: 1100px) {
      .header-links { display: none !important; }
      .mobile-toggle-btn { display: block !important; }
    }
  </style>
  {% block extrahead %}{% endblock %}
</head>
<body>

<!-- EXECUTIVE ADMIN NAVBAR (DIRECT TABS, NO CONFUSING DROPDOWNS) -->
<header class="unified-header">
  <div class="header-container">
    
    <!-- Left: Brand Logo -->
    <a href="{% url 'home' %}" class="header-brand">
      <div class="brand-logo-wrapper">
        <img src="{% static 'images/meatflow_logo.jpg' %}" class="brand-logo-img" alt="MeatFlow Pro">
      </div>
      <div>
        <span class="brand-name">MeatFlow <span style="color:#10B981;">Pro</span></span>
        <span class="brand-sub">{{ store.name|default:"BAXMAL MEAT BOUTIQUE" }}</span>
      </div>
    </a>

    <!-- Center: All Direct Admin Navigation Tabs -->
    {% if user.is_superuser %}
    <div class="header-links">
      <a href="{% url 'home' %}" class="header-link-item {% if request.resolver_match.url_name == 'home' %}active{% endif %}">
        <i class="bi bi-grid-fill"></i> Boshqaruv
      </a>
      <a href="{% url 'terminal' %}" class="header-link-item {% if request.resolver_match.url_name == 'terminal' %}active{% endif %}">
        <i class="bi bi-display-fill"></i> Terminal (Kassa)
      </a>
      <a href="{% url 'customers' %}" class="header-link-item {% if request.resolver_match.url_name == 'customers' or request.resolver_match.url_name == 'customer_chats_dashboard' %}active{% endif %}">
        <i class="bi bi-people-fill"></i> Mijozlar
      </a>
      <a href="{% url 'article_list' %}" class="header-link-item {% if 'article' in request.resolver_match.url_name %}active{% endif %}">
        <i class="bi bi-box-seam-fill"></i> Ombor
      </a>
      <a href="{% url 'yield_loss' %}" class="header-link-item {% if request.resolver_match.url_name == 'yield_loss' %}active{% endif %}">
        <i class="bi bi-calculator-fill"></i> Tannarx
      </a>
      <a href="{% url 'cash_flow' %}" class="header-link-item {% if request.resolver_match.url_name == 'cash_flow' or request.resolver_match.url_name == 'debt_payment' %}active{% endif %}">
        <i class="bi bi-cash-stack"></i> Kassa
      </a>
      <a href="{% url 'daily_report' %}" class="header-link-item {% if request.resolver_match.url_name == 'daily_report' or request.resolver_match.url_name == 'global_analytics' %}active{% endif %}">
        <i class="bi bi-graph-up-arrow"></i> Analitika
      </a>
      <a href="{% url 'ai_assistant_page' %}" class="header-link-item ai-link-item {% if request.resolver_match.url_name == 'ai_assistant_page' %}active{% endif %}">
        <i class="bi bi-robot"></i> AI Yordamchi
      </a>
    </div>
    {% endif %}

    <!-- Right: Controls (Script, Notification, Profile Dropdown) -->
    <div class="header-actions">
      
      <!-- Script Switcher -->
      <div class="script-toggle-compact">
        <a href="/pos/switch-script/latin/" class="script-btn-compact {% if request.session.script_mode == 'latin' or not request.session.script_mode %}active{% endif %}">Lotin</a>
        <a href="/pos/switch-script/cyrillic/" class="script-btn-compact {% if request.session.script_mode == 'cyrillic' %}active{% endif %}">Кирилл</a>
      </div>

      <!-- Phone Link -->
      <a href="tel:+998770824477" class="d-none d-xxl-inline text-white-50 font-12 text-decoration-none" style="font-size: 12px;">
        <i class="bi bi-telephone-fill text-warning me-1"></i> +998 77 082 4477
      </a>

      <!-- Notification Bell -->
      {% if user.is_authenticated and user.is_superuser %}
      <div class="dropdown" id="notificationDropdownWrapper">
        <button class="btn btn-sm btn-link text-decoration-none position-relative p-0 text-white opacity-80" type="button" data-bs-toggle="dropdown" onclick="loadNotifications()">
          <i class="bi bi-bell-fill font-16" style="color: #D4A853;"></i>
          <span id="notif-count-badge" class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="font-size: 8px; padding: 2px 4px; display: none;">0</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end shadow-md p-2 mt-2" id="notificationDropdownMenu" style="width: 290px; border-radius: 14px;">
          <li class="dropdown-header border-bottom pb-2 fw-bold text-uppercase style-main" style="font-size: 11px; color: var(--primary);">🔔 Bildirishnomalar</li>
          <div id="notif-list-container" style="max-height: 250px; overflow-y: auto;">
            <li class="text-center py-3 text-muted">Yuklanmoqda...</li>
          </div>
        </ul>
      </div>
      {% endif %}

      <!-- User Avatar / Profile Dropdown -->
      {% if user.is_authenticated %}
      <div class="dropdown">
        <button class="btn btn-sm btn-link text-decoration-none dropdown-toggle p-0 d-flex align-items-center gap-2 text-white" type="button" id="adminProfileDropdown" data-bs-toggle="dropdown" aria-expanded="false">
          <div style="width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #10B981, #059669); color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; border: 1px solid rgba(255,255,255,0.3);">
            {{ user.username|slice:":1"|upper }}
          </div>
          <span class="d-none d-md-inline" style="font-size: 13px; font-weight: 600;">{{ user.username }}</span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end shadow-lg" aria-labelledby="adminProfileDropdown" style="border-radius: 14px; padding: 8px; min-width: 230px; border: 1px solid rgba(0,0,0,0.1); background: #FFFFFF; z-index: 1200;">
          <div class="px-3 py-2 border-bottom mb-2">
            <div class="fw-bold text-dark" style="font-size: 13px;">{{ user.get_full_name|default:user.username }}</div>
            <div class="text-muted" style="font-size: 11px;">{% if user.is_superuser %}Administrator{% else %}Mijoz{% endif %}</div>
          </div>
          {% if user.is_superuser %}
          <li><a class="dropdown-item rounded-2 py-2 fw-semibold" href="/admin/pos/storesetting/"><i class="bi bi-gear-fill me-2 text-warning"></i> Do'kon & Aksiya Sozlamalari</a></li>
          <li><a class="dropdown-item rounded-2 py-2 fw-semibold" href="/admin/"><i class="bi bi-database-check me-2 text-primary"></i> Django Admin</a></li>
          <li><a class="dropdown-item rounded-2 py-2 fw-semibold" href="{% url 'suppliers_dashboard' %}"><i class="bi bi-truck me-2 text-dark"></i> Ta'minotchilar</a></li>
          <li><a class="dropdown-item rounded-2 py-2 fw-semibold" href="{% url 'debt-migration' %}"><i class="bi bi-journal-arrow-up me-2 text-secondary"></i> Nasiya Ko'chirish</a></li>
          {% else %}
          <li><a class="dropdown-item rounded-2 py-2 fw-semibold" href="/pos/my-cabinet/"><i class="bi bi-person-vcard me-2 text-success"></i> Shaxsiy Kabinet</a></li>
          {% endif %}
          <li><hr class="dropdown-divider"></li>
          <li>
            <form action="{% url 'logout' %}" method="post" class="m-0">
              {% csrf_token %}
              <button type="submit" class="dropdown-item text-danger rounded-2 py-2 fw-semibold"><i class="bi bi-box-arrow-right me-2"></i> Chiqish</button>
            </form>
          </li>
        </ul>
      </div>
      {% else %}
      <a href="{% url 'login' %}" style="color: #FFFFFF; font-weight: 600; text-decoration: none; font-size: 12px;">Kirish</a>
      <a href="{% url 'signup' %}" style="color: #061A13; background: #D4A853; padding: 5px 14px; border-radius: 30px; text-decoration: none; font-weight: 700; font-size: 12px;">Ro'yxatdan o'tish</a>
      {% endif %}

      <!-- Mobile Toggle -->
      <button class="mobile-toggle-btn" onclick="toggleMobileNavbar()">
        <i class="bi bi-list"></i>
      </button>

    </div>

  </div>
</header>

<!-- Mobile Menu Drawer -->
<div id="mobile-navbar-dropdown" class="mobile-menu-drawer">
  <div class="d-flex flex-column gap-2">
    {% if user.is_superuser %}
    <a href="{% url 'home' %}" class="header-link-item"><i class="bi bi-grid-fill"></i> Boshqaruv Paneli</a>
    <a href="{% url 'terminal' %}" class="header-link-item"><i class="bi bi-display-fill"></i> Savdo Terminali</a>
    <a href="{% url 'customers' %}" class="header-link-item"><i class="bi bi-people-fill"></i> Mijozlar Bazasi</a>
    <a href="{% url 'article_list' %}" class="header-link-item"><i class="bi bi-box-seam-fill"></i> Ombor</a>
    <a href="{% url 'yield_loss' %}" class="header-link-item"><i class="bi bi-calculator-fill"></i> Tannarx</a>
    <a href="{% url 'cash_flow' %}" class="header-link-item"><i class="bi bi-cash-stack"></i> Kassa</a>
    <a href="{% url 'daily_report' %}" class="header-link-item"><i class="bi bi-graph-up-arrow"></i> Analitika</a>
    <a href="{% url 'ai_assistant_page' %}" class="header-link-item ai-link-item"><i class="bi bi-robot"></i> AI Yordamchi</a>
    {% else %}
    <a href="/pos/my-cabinet/" class="header-link-item"><i class="bi bi-person-vcard"></i> Shaxsiy Kabinet</a>
    {% endif %}
  </div>
</div>

<script>
function toggleMobileNavbar() {
  const menu = document.getElementById('mobile-navbar-dropdown');
  if (menu) menu.classList.toggle('show');
}
</script>

<div class="main-wrapper">
  {% block content %}{% endblock content %}
</div>

<!-- KATTA AKSIYA PROMO MODAL -->
{% if store and store.promo_banner_text %}
<div class="modal fade" id="promoBannerModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0 shadow-lg" style="border-radius: 20px; overflow: hidden; background: #FFFFFF;">
      <div style="background: linear-gradient(135deg, #051610, #1B6B4A); color: #FFFFFF; padding: 24px; text-align: center; position: relative;">
        <button type="button" class="btn-close btn-close-white position-absolute top-0 end-0 m-3" data-bs-dismiss="modal" aria-label="Close"></button>
        <span class="badge bg-warning text-dark font-monospace fw-bold mb-2 px-3 py-2" style="font-size: 11px; letter-spacing: 1px; border-radius: 30px;">🔥 KATTA AKSIYA & MAXSUS TAKLIF</span>
        <h4 style="font-family: 'DM Serif Display', serif; margin: 8px 0 0; color: #D4A853;">Baxmal Meat Boutique</h4>
      </div>
      <div class="modal-body p-4 text-center">
        <div style="font-size: 15px; color: #1A1A2E; line-height: 1.6; margin-bottom: 24px; font-weight: 500;">
          {{ store.promo_banner_text|safe }}
        </div>
        <div style="background: rgba(16,185,129,0.08); border-radius: 12px; padding: 12px; font-size: 12.5px; color: #10B981; font-weight: 600; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 8px;">
          <i class="bi bi-truck-flatbed font-18"></i> 100% Halol Kafolatli va Tezkor Yetkazish!
        </div>
        <a href="/pos/my-cabinet/" class="btn btn-success rounded-pill fw-bold w-100 py-3 style-main" style="background: linear-gradient(135deg, #1B6B4A, #145438); border: none; font-size: 14px; box-shadow: 0 4px 15px rgba(27,107,74,0.3);">
          Buyurtma Berish <i class="bi bi-arrow-right ms-1"></i>
        </a>
      </div>
    </div>
  </div>
</div>
{% endif %}

<footer class="modern-footer" style="background: #051610; color: rgba(255,255,255,0.7); padding: 32px 24px; margin-top: 60px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 13px;">
  <div style="max-width: 1440px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
    <div>
      © 2026 <strong style="color: #FFFFFF;">Baxmal Meat Boutique</strong>. Barcha huquqlar himoyalangan.
    </div>
    <div style="display: flex; gap: 16px;">
      <a href="tel:+998770824477" style="color: #D4A853; text-decoration: none;"><i class="bi bi-telephone me-1"></i> +998 77 082 4477</a>
      <span style="color: rgba(255,255,255,0.2);">|</span>
      <span>Toshkent shahri, Chilonzor tumani</span>
    </div>
  </div>
</footer>

<script>
function loadNotifications() {
  fetch('/pos/api/notifications/')
    .then(r => r.json())
    .then(data => {
      const container = document.getElementById('notif-list-container');
      const badge = document.getElementById('notif-count-badge');
      if (!container) return;
      if (data.count > 0) {
        if (badge) { badge.textContent = data.count; badge.style.display = 'block'; }
        container.innerHTML = data.items.map(i => `
          <li class="p-2 border-bottom hover-bg-light" style="font-size: 11.5px;">
            <div class="fw-bold text-dark">${i.title}</div>
            <div class="text-muted">${i.message}</div>
          </li>
        `).join('');
      } else {
        if (badge) badge.style.display = 'none';
        container.innerHTML = '<li class="text-center py-3 text-muted">Yangi bildirishnoma yo\'q</li>';
      }
    });
}

// Universal Dropdown Toggle Listener
document.addEventListener('click', function(e) {
  const toggleBtn = e.target.closest('[data-bs-toggle="dropdown"], .dropdown-toggle');
  if (toggleBtn) {
    e.preventDefault();
    e.stopPropagation();
    const dropdownParent = toggleBtn.closest('.dropdown');
    if (dropdownParent) {
      const menu = dropdownParent.querySelector('.dropdown-menu');
      if (menu) {
        document.querySelectorAll('.dropdown-menu.show').forEach(m => {
          if (m !== menu) m.classList.remove('show');
        });
        menu.classList.toggle('show');
      }
    }
  } else if (!e.target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown-menu.show').forEach(m => m.classList.remove('show'));
  }
});
</script>
{% block extrascripts %}{% endblock %}

</body>
</html>
'''

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(new_base_html)
print("SUCCESSFULLY_FIXED_ADMIN_NAVBAR")
