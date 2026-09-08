# -*- coding: utf-8 -*-
import sys

base_html_code = '''{% load static %}
<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}MeatFlow Pro | Baxmal Meat Boutique{% endblock %}</title>
  
  <!-- Favicon -->
  <link rel="icon" type="image/jpeg" href="{% static 'images/meatflow_logo.jpg' %}">
  
  <!-- Bootstrap 5 CSS & Icons -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
  
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

    /* ── BULLETPROOF EXECUTIVE NAVBAR ── */
    .unified-header {
      background: linear-gradient(135deg, #04120C 0%, #08261A 50%, #04140D 100%);
      border-bottom: 1px solid rgba(212, 168, 83, 0.35);
      padding: 10px 0;
      position: sticky;
      top: 0;
      z-index: 1050;
      box-shadow: 0 8px 30px rgba(0,0,0,0.35);
      backdrop-filter: blur(14px);
    }
    
    /* Brand Logo */
    .header-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }
    .brand-logo-wrapper {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      padding: 2px;
      background: linear-gradient(135deg, #10B981, #D4A853);
      box-shadow: 0 4px 16px rgba(16,185,129,0.35);
    }
    .brand-logo-img {
      width: 100%;
      height: 100%;
      border-radius: 10px;
      object-fit: cover;
    }
    .brand-name {
      font-family: var(--font-main);
      font-size: 19px;
      font-weight: 800;
      color: #FFFFFF;
      letter-spacing: -0.3px;
      line-height: 1;
    }
    .brand-sub {
      font-size: 8.5px;
      color: var(--accent);
      letter-spacing: 1.5px;
      text-transform: uppercase;
      font-weight: 700;
      margin-top: 2px;
      display: block;
    }

    /* VIBRANT ACTION PILLS */
    .nav-pill-item {
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
      padding: 7px 15px;
      border-radius: 50px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.22s ease;
      white-space: nowrap;
      border: 1px solid transparent;
    }
    .nav-pill-item:hover {
      transform: translateY(-1px);
    }

    /* Pill Colors */
    .pill-green {
      color: #10B981;
      background: rgba(16, 185, 129, 0.14);
      border-color: rgba(16, 185, 129, 0.3);
    }
    .pill-green:hover, .pill-green.active {
      background: #10B981;
      color: #04120C !important;
      box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
    }

    .pill-blue {
      color: #60A5FA;
      background: rgba(96, 165, 250, 0.14);
      border-color: rgba(96, 165, 250, 0.3);
    }
    .pill-blue:hover, .pill-blue.active {
      background: #3B82F6;
      color: #FFFFFF !important;
      box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
    }

    .pill-purple {
      color: #C084FC;
      background: rgba(192, 132, 252, 0.14);
      border-color: rgba(192, 132, 252, 0.3);
    }
    .pill-purple:hover, .pill-purple.active {
      background: #A855F7;
      color: #FFFFFF !important;
      box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
    }

    .pill-amber {
      color: #FBBF24;
      background: rgba(251, 191, 36, 0.14);
      border-color: rgba(251, 191, 36, 0.3);
    }
    .pill-amber:hover, .pill-amber.active {
      background: #F59E0B;
      color: #04120C !important;
      box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
    }

    .pill-indigo {
      color: #818CF8;
      background: rgba(129, 140, 248, 0.14);
      border-color: rgba(129, 140, 248, 0.3);
    }
    .pill-indigo:hover, .pill-indigo.active {
      background: #6366F1;
      color: #FFFFFF !important;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    .pill-pink {
      color: #F472B6;
      background: rgba(244, 114, 182, 0.14);
      border-color: rgba(244, 114, 182, 0.3);
    }
    .pill-pink:hover, .pill-pink.active {
      background: linear-gradient(135deg, #EC4899, #D946EF);
      color: #FFFFFF !important;
      box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
    }

    /* Script Switcher */
    .script-pill-toggle {
      display: inline-flex;
      background: rgba(255,255,255,0.12);
      border-radius: 30px;
      padding: 2px;
      border: 1px solid rgba(212,168,83,0.3);
    }
    .script-pill {
      color: rgba(255,255,255,0.85);
      text-decoration: none;
      font-size: 11px;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 30px;
      transition: all 0.2s;
    }
    .script-pill.active {
      background: #10B981;
      color: #FFFFFF !important;
      box-shadow: 0 2px 8px rgba(16,185,129,0.5);
    }

    /* User Profile Dropdown Button */
    .btn-user-profile {
      background: linear-gradient(135deg, rgba(16,185,129,0.22), rgba(212,168,83,0.22));
      border: 1.5px solid #D4A853 !important;
      color: #FFFFFF !important;
      padding: 4px 12px 4px 6px;
      border-radius: 50px;
      font-size: 13px;
      font-weight: 800;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 4px 14px rgba(0,0,0,0.2);
    }
    .btn-user-profile:hover {
      background: rgba(212,168,83,0.35);
      border-color: #F59E0B !important;
    }
    .user-avatar-circle {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10B981, #D4A853);
      color: #04120C;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 13px;
    }
  </style>
  {% block extrahead %}{% endblock %}
</head>
<body>

<!-- BULLETPROOF HEADER NAVBAR -->
<header class="unified-header">
  <div class="container-fluid px-lg-4">
    <nav class="navbar navbar-expand-lg navbar-dark p-0">
      
      <!-- Left: Logo -->
      <a href="{% url 'home' %}" class="header-brand me-3">
        <div class="brand-logo-wrapper">
          <img src="{% static 'images/meatflow_logo.jpg' %}" class="brand-logo-img" alt="MeatFlow Pro">
        </div>
        <div>
          <span class="brand-name">MeatFlow <span style="color:#10B981;">Pro</span></span>
          <span class="brand-sub">{{ store.name|default:"BAXMAL MEAT BOUTIQUE" }}</span>
        </div>
      </a>

      <!-- Mobile Hamburger Button -->
      <button class="navbar-toggler border-0 shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#mainHeaderNavbar" aria-controls="mainHeaderNavbar" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>

      <!-- Navbar Collapsible Menu -->
      <div class="collapse navbar-collapse" id="mainHeaderNavbar">
        
        <!-- Center Links (Admin vs Customer) -->
        <div class="navbar-nav mx-auto d-flex flex-wrap gap-2 my-2 my-lg-0">
          {% if user.is_superuser %}
            <a href="{% url 'home' %}" class="nav-pill-item pill-green {% if request.resolver_match.url_name == 'home' %}active{% endif %}">
              <i class="bi bi-grid-1x2-fill"></i> Boshqaruv
            </a>
            <a href="{% url 'terminal' %}" class="nav-pill-item pill-blue {% if request.resolver_match.url_name == 'terminal' %}active{% endif %}">
              <i class="bi bi-display-fill"></i> Terminal (Kassa)
            </a>
            <a href="{% url 'customers' %}" class="nav-pill-item pill-purple {% if request.resolver_match.url_name == 'customers' or request.resolver_match.url_name == 'customer_chats_dashboard' %}active{% endif %}">
              <i class="bi bi-people-fill"></i> Mijozlar
            </a>
            <a href="{% url 'article_list' %}" class="nav-pill-item pill-amber {% if 'article' in request.resolver_match.url_name %}active{% endif %}">
              <i class="bi bi-box-seam-fill"></i> Ombor
            </a>
            
            <div class="nav-item dropdown">
              <a class="nav-pill-item pill-indigo dropdown-toggle text-decoration-none" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                <i class="bi bi-bar-chart-line-fill"></i> Moliya &amp; Hisobot
              </a>
              <ul class="dropdown-menu shadow-lg border-0 rounded-4 p-2 mt-2">
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'cash_flow' %}"><i class="bi bi-cash-stack me-2 text-success"></i> Kirim-Chiqim (Kassa)</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'yield_loss' %}"><i class="bi bi-calculator-fill me-2 text-warning"></i> So'yim &amp; Tannarx</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'daily_report' %}"><i class="bi bi-calendar-check me-2 text-info"></i> Kunlik Hisob-kitob</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'global_analytics' %}"><i class="bi bi-graph-up-arrow me-2 text-primary"></i> Kengaytirilgan Analitika</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'debt_payment' %}"><i class="bi bi-wallet2 me-2 text-danger"></i> Qarzlar To'lovi</a></li>
              </ul>
            </div>

            <a href="{% url 'ai_assistant_page' %}" class="nav-pill-item pill-pink {% if request.resolver_match.url_name == 'ai_assistant_page' %}active{% endif %}">
              <i class="bi bi-robot"></i> AI Qassob
            </a>
          {% else %}
            <a href="{% url 'home' %}" class="nav-pill-item pill-green {% if request.resolver_match.url_name == 'home' %}active{% endif %}">
              <i class="bi bi-house-door-fill"></i> Bosh Sahifa
            </a>
            <a href="{% url 'article_list' %}" class="nav-pill-item pill-amber {% if 'article' in request.resolver_match.url_name %}active{% endif %}">
              <i class="bi bi-shop"></i> Go'sht Katalogi
            </a>
            <a href="/pos/my-cabinet/" class="nav-pill-item pill-purple {% if 'cabinet' in request.path %}active{% endif %}">
              <i class="bi bi-cart-check-fill"></i> Buyurtma &amp; Kabinet
            </a>
          {% endif %}
        </div>

        <!-- Right: Controls & User Profile -->
        <div class="d-flex align-items-center gap-2 mt-2 mt-lg-0">
          
          <!-- Script Switcher -->
          <div class="script-pill-toggle">
            <a href="/pos/switch-script/latin/" class="script-pill {% if request.session.script_mode != 'cyrillic' %}active{% endif %}">Lotin</a>
            <a href="/pos/switch-script/cyrillic/" class="script-pill {% if request.session.script_mode == 'cyrillic' %}active{% endif %}">Кирилл</a>
          </div>

          <!-- Notification Bell (Superuser only) -->
          {% if user.is_authenticated and user.is_superuser %}
          <div class="dropdown">
            <button class="btn btn-outline-warning btn-sm rounded-circle p-0" style="width:36px; height:36px;" type="button" data-bs-toggle="dropdown" onclick="loadNotifications()">
              <i class="bi bi-bell-fill"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 rounded-4 p-2 mt-2" style="width: 300px;">
              <div class="px-3 py-2 border-bottom d-flex align-items-center justify-content-between mb-2">
                <span class="fw-bold text-dark font-12 text-uppercase">🔔 Bildirishnomalar</span>
                <span class="badge bg-success bg-opacity-10 text-success font-10">Real vaqt</span>
              </div>
              <div id="notif-list-container" style="max-height: 250px; overflow-y: auto;">
                <li class="text-center py-3 text-muted">Yuklanmoqda...</li>
              </div>
            </ul>
          </div>
          {% endif %}

          <!-- User Profile Dropdown -->
          {% if user.is_authenticated %}
          <div class="dropdown">
            <button class="btn btn-user-profile dropdown-toggle border-0" type="button" data-bs-toggle="dropdown" aria-expanded="false">
              <div class="user-avatar-circle">
                {{ user.username|slice:":1"|upper }}
              </div>
              <span>{{ user.username }}</span>
            </button>

            <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 rounded-4 p-2 mt-2" style="min-width: 260px;">
              <div class="px-3 py-2 border-bottom mb-2">
                <div class="fw-bold text-dark font-14">{{ user.get_full_name|default:user.username }}</div>
                <div class="text-success font-11 fw-bold">{% if user.is_superuser %}⚡ Bosh Administrator{% else %}👤 Mijoz{% endif %}</div>
              </div>
              
              {% if user.is_superuser %}
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'home' %}"><i class="bi bi-grid-1x2-fill me-2 text-success"></i> Boshqaruv Paneli</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'terminal' %}"><i class="bi bi-display-fill me-2 text-primary"></i> Savdo Terminali</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'customers' %}"><i class="bi bi-people-fill me-2 text-purple"></i> Mijozlar Bazasi &amp; CRM</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'article_list' %}"><i class="bi bi-box-seam-fill me-2 text-warning"></i> Ombor &amp; Go'shtlar</a></li>
                <li><hr class="dropdown-divider my-2"></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="/admin/pos/storesetting/"><i class="bi bi-sliders me-2 text-warning"></i> Sarlavha &amp; Aksiya Sozlamalari</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'suppliers_dashboard' %}"><i class="bi bi-truck me-2 text-info"></i> Ta'minotchilar Portali</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'debt-migration' %}"><i class="bi bi-journal-arrow-up me-2 text-secondary"></i> Daftardan Qarz Ko'chirish</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="/admin/"><i class="bi bi-database-gear me-2 text-primary"></i> Django Admin</a></li>
              {% else %}
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'home' %}"><i class="bi bi-house-door-fill me-2 text-success"></i> Bosh Sahifa</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="{% url 'article_list' %}"><i class="bi bi-shop me-2 text-warning"></i> Go'sht Katalogi</a></li>
                <li><a class="dropdown-item rounded-3 py-2 fw-semibold" href="/pos/my-cabinet/"><i class="bi bi-person-vcard me-2 text-primary"></i> Shaxsiy Kabinet &amp; Buyurtmalarim</a></li>
              {% endif %}

              <li><hr class="dropdown-divider my-2"></li>
              <li>
                <form action="{% url 'logout' %}" method="post" class="m-0">
                  {% csrf_token %}
                  <button type="submit" class="dropdown-item text-danger rounded-3 py-2 fw-semibold"><i class="bi bi-box-arrow-right me-2"></i> Tizimdan Chiqish</button>
                </form>
              </li>
            </ul>
          </div>
          {% else %}
          <a href="{% url 'login' %}" class="btn btn-outline-light btn-sm rounded-pill font-12 fw-bold px-3">Kirish</a>
          <a href="{% url 'signup' %}" class="btn btn-warning btn-sm rounded-pill font-12 fw-bold px-3 text-dark">Ro'yxatdan o'tish</a>
          {% endif %}

        </div>

      </div>
    </nav>
  </div>
</header>

<div class="main-wrapper">
  {% block content %}{% endblock content %}
</div>

<!-- LUXURY FOOTER -->
<footer style="background: #04120C; color: rgba(255,255,255,0.7); padding: 48px 24px 32px; border-top: 1px solid rgba(212,168,83,0.2); font-size: 13.5px; margin-top: 60px;">
  <div style="max-width: 1440px; margin: 0 auto;" class="row g-4">
    
    <div class="col-lg-4 col-md-6">
      <div class="d-flex align-items-center gap-2 mb-3">
        <div style="width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #10B981, #D4A853); display: flex; align-items: center; justify-content: center; color: #FFF; font-weight: 800;">M</div>
        <span class="h5 fw-bold text-white mb-0">MeatFlow <span style="color:#10B981;">Pro</span></span>
      </div>
      <p style="color: rgba(255,255,255,0.6); line-height: 1.6; max-width: 340px;">
        Baxmal Meat Boutique — Fermadan to'g'ridan-to'g'ri dasturxoningizga 100% Halol, muzlatilmagan sarxil mol va qo'y go'shtlari, shaffof tarozi va tezkor kuryerlik xizmati.
      </p>
      <div class="d-flex align-items-center gap-2 text-success font-12 fw-bold">
        <i class="bi bi-patch-check-fill font-16"></i> 100% Halol &amp; Yaylov Sifat Kafolati
      </div>
    </div>

    {% if user.is_superuser %}
    <!-- Admin Footer Navigation -->
    <div class="col-lg-3 col-md-6">
      <h6 class="text-white fw-bold mb-3 text-uppercase font-12" style="letter-spacing: 1px; color: #D4A853 !important;">Boshqaruv Havolalari</h6>
      <ul class="list-unstyled d-flex flex-column gap-2 mb-0">
        <li><a href="{% url 'home' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Boshqaruv Paneli</a></li>
        <li><a href="{% url 'terminal' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Savdo Terminali (Kassa)</a></li>
        <li><a href="{% url 'customers' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Mijozlar Bazasi &amp; CRM</a></li>
        <li><a href="{% url 'article_list' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Ombor &amp; Go'sht Katalogi</a></li>
      </ul>
    </div>

    <div class="col-lg-2 col-md-6">
      <h6 class="text-white fw-bold mb-3 text-uppercase font-12" style="letter-spacing: 1px; color: #D4A853 !important;">Analitika &amp; Kassa</h6>
      <ul class="list-unstyled d-flex flex-column gap-2 mb-0">
        <li><a href="{% url 'cash_flow' %}" class="text-white-50 text-decoration-none"><i class="bi bi-chevron-right font-10 text-warning me-1"></i> Kirim-Chiqim Kassa</a></li>
        <li><a href="{% url 'yield_loss' %}" class="text-white-50 text-decoration-none"><i class="bi bi-chevron-right font-10 text-warning me-1"></i> So'yim &amp; Tannarx</a></li>
        <li><a href="{% url 'daily_report' %}" class="text-white-50 text-decoration-none"><i class="bi bi-chevron-right font-10 text-warning me-1"></i> Analitika Hisoboti</a></li>
        <li><a href="{% url 'ai_assistant_page' %}" class="text-white-50 text-decoration-none"><i class="bi bi-chevron-right font-10 text-warning me-1"></i> AI Qassob Maslahatchisi</a></li>
      </ul>
    </div>
    {% else %}
    <!-- Customer Footer Navigation -->
    <div class="col-lg-3 col-md-6">
      <h6 class="text-white fw-bold mb-3 text-uppercase font-12" style="letter-spacing: 1px; color: #D4A853 !important;">Tezkor Havolalar</h6>
      <ul class="list-unstyled d-flex flex-column gap-2 mb-0">
        <li><a href="{% url 'home' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Bosh Sahifa</a></li>
        <li><a href="{% url 'article_list' %}" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Sarxil Go'shtlar Katalogi</a></li>
        <li><a href="/pos/my-cabinet/" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Shaxsiy Kabinet &amp; Buyurtmalar</a></li>
        <li><a href="tel:+998770824477" class="text-white-50 text-decoration-none hover-white"><i class="bi bi-chevron-right font-10 text-success me-1"></i> Biz Bilan Bog'lanish</a></li>
      </ul>
    </div>

    <div class="col-lg-2 col-md-6">
      <h6 class="text-white fw-bold mb-3 text-uppercase font-12" style="letter-spacing: 1px; color: #D4A853 !important;">Afzalliklarimiz</h6>
      <ul class="list-unstyled d-flex flex-column gap-2 mb-0 text-white-50 font-13">
        <li><i class="bi bi-check2-circle text-success me-1"></i> 100% Halol Yaylov Go'shti</li>
        <li><i class="bi bi-check2-circle text-success me-1"></i> Shoshilinch Kuryerlik</li>
        <li><i class="bi bi-check2-circle text-success me-1"></i> Shaffof Tarozi Hisobi</li>
        <li><i class="bi bi-check2-circle text-success me-1"></i> Cashback &amp; Bonuslar</li>
      </ul>
    </div>
    {% endif %}

    <div class="col-lg-3 col-md-6">
      <h6 class="text-white fw-bold mb-3 text-uppercase font-12" style="letter-spacing: 1px; color: #D4A853 !important;">Bog'lanish</h6>
      <div class="d-flex flex-column gap-2 text-white-50 font-13">
        <div><i class="bi bi-telephone-fill text-warning me-2"></i> +998 77 082 4477</div>
        <div><i class="bi bi-geo-alt-fill text-danger me-2"></i> Toshkent sh., Chilonzor t.</div>
        <div><i class="bi bi-clock-fill text-info me-2"></i> Har kuni: 08:00 - 22:00</div>
      </div>
    </div>

  </div>

  <div style="max-width: 1440px; margin: 32px auto 0; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 20px;" class="d-flex justify-content-between align-items-center flex-wrap gap-2 font-12 text-white-50">
    <div>© 2026 <strong>Baxmal Meat Boutique</strong>. Barcha huquqlar himoyalangan.</div>
    <div>Sifatli va Isbotlangan Halol Mahsulotlar</div>
  </div>
</footer>

<!-- Single Bootstrap 5 JS Import at bottom -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/bootstrap.bundle.min.js"></script>

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
</script>
{% block extrascripts %}{% endblock %}

</body>
</html>
'''

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(base_html_code)
print("SUCCESSFULLY_BUILT_BULLETPROOF_HEADER")
