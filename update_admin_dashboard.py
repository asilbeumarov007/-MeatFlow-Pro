# -*- coding: utf-8 -*-
import sys

new_admin_part = '''{% extends 'base.html' %}
{% load static %}

{% block title %}
  {% if user.is_authenticated and user.is_superuser %}
    MeatFlow Pro — Analitika & Boshqaruv
  {% else %}
    {{ store.name|default:"MeatFlow Pro | Baxmal Meat Boutique" }}
  {% endif %}
{% endblock title %}

{% block content %}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

{% if user.is_authenticated and user.is_superuser %}
<!-- ========================================================================
     MEATFLOW PRO: EXECUTIVE MANAGER DASHBOARD
     ======================================================================== -->
<style>
  body {
    background-color: #F4F6F5 !important;
  }

  .mfp-tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 18px;
    border-radius: 50px;
    text-decoration: none;
    font-size: 13.5px;
    font-weight: 600;
    color: #4B5563;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .mfp-tab:hover {
    color: #1B6B4A !important;
    background: rgba(27,107,74,0.06);
  }
  .mfp-tab.active {
    color: #1B6B4A !important;
    background: rgba(27,107,74,0.12);
    font-weight: 700;
    box-shadow: inset 0 0 0 1px rgba(27,107,74,0.2);
  }

  .mfp-card {
    background: #FFFFFF;
    border-radius: 20px;
    padding: 24px;
    border: 1px solid rgba(0,0,0,0.05);
    height: 100%;
    box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .mfp-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.06);
  }

  .quick-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 13px;
    text-decoration: none;
    transition: all 0.2s ease;
  }
  .quick-action-btn-primary {
    background: linear-gradient(135deg, #1B6B4A, #145438);
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(27,107,74,0.25);
  }
  .quick-action-btn-primary:hover {
    box-shadow: 0 6px 20px rgba(27,107,74,0.35);
    transform: translateY(-1px);
  }
  .quick-action-btn-secondary {
    background: #FFFFFF;
    color: #1A1A2E !important;
    border: 1px solid rgba(0,0,0,0.1);
  }
  .quick-action-btn-secondary:hover {
    background: #F9FAFB;
    border-color: #1B6B4A;
    color: #1B6B4A !important;
  }
</style>

<div class="mfp-container animate__animated animate__fadeIn" style="max-width: 1440px; margin: 0 auto; padding: 28px 24px 60px; font-family: 'Inter', system-ui, sans-serif;">
  
  <!-- Executive Top Header -->
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 24px;">
    <div>
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
        <h2 style="font-family: 'DM Serif Display', serif; font-size: 2.2rem; color: #1A1A2E; margin: 0; font-weight: 400;">
          <span id="dynamic-greeting">Xayrli kun</span>, {{ user.get_full_name|default:user.username }}! 👋
        </h2>
        <span class="badge bg-success bg-opacity-10 text-success fw-bold px-3 py-2 rounded-pill" style="font-size: 11px; letter-spacing: 0.5px;">
          <i class="bi bi-circle-fill text-success me-1" style="font-size: 8px;"></i> ONLAYN
        </span>
      </div>
      <p style="margin: 0; color: #6B7280; font-size: 13.5px;">
        Baxmal Meat Boutique — Real vaqtidagi boshqaruv paneli va savdo analitikasi
      </p>
    </div>

    <!-- Quick Executive Actions -->
    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
      <a href="/admin/pos/storesetting/" class="quick-action-btn quick-action-btn-secondary">
        <i class="bi bi-sliders text-warning"></i> Sarlavha & Aksiya Sozlamalari
      </a>
      <a href="/admin/pos/slaughter/add/" class="quick-action-btn quick-action-btn-primary">
        <i class="bi bi-plus-circle-fill"></i> So'yim Qo'shish
      </a>
    </div>
  </div>

  <!-- Header Navigation Ribbon -->
  <div style="background: #FFFFFF; border-radius: 20px; padding: 10px 16px; border: 1px solid rgba(0,0,0,0.06); margin-bottom: 28px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
      <a href="{% url 'home' %}" class="mfp-tab active">
        <i class="bi bi-grid-fill"></i> Boshqaruv Paneli
      </a>
      <a href="{% url 'terminal' %}" class="mfp-tab">
        <i class="bi bi-display-fill"></i> Savdo Terminali
      </a>
      <a href="{% url 'customers' %}" class="mfp-tab">
        <i class="bi bi-people-fill"></i> Mijozlar
      </a>
      <a href="{% url 'article_list' %}" class="mfp-tab">
        <i class="bi bi-box-seam-fill"></i> Ombor
      </a>
      <a href="{% url 'yield_loss' %}" class="mfp-tab">
        <i class="bi bi-calculator-fill"></i> Tannarx
      </a>
      <a href="{% url 'cash_flow' %}" class="mfp-tab">
        <i class="bi bi-cash-stack"></i> Kassa
      </a>
      <a href="{% url 'ai_assistant_page' %}" class="mfp-tab" style="color: #92650A; background: rgba(212,168,83,0.12);">
        <i class="bi bi-robot" style="color: #D4A853;"></i> AI Maslahatchi
      </a>
    </div>
  </div>

  <!-- KPI Stat Grid -->
  <div class="row g-4 mb-4">
    <!-- Card 1: Revenue -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <span style="font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;">Bugungi Savdo</span>
          <div style="width: 42px; height: 42px; border-radius: 14px; background: rgba(27,107,74,0.1); color: #1B6B4A; display: flex; align-items: center; justify-content: center; font-size: 20px;">
            <i class="bi bi-wallet2"></i>
          </div>
        </div>
        <div style="font-size: 26px; font-weight: 800; color: #1A1A2E; letter-spacing: -0.5px;">
          {{ today_revenue|default:0|floatformat:0 }} <span style="font-size: 14px; color: #6B7280; font-weight: 500;">so'm</span>
        </div>
        <div style="font-size: 12.5px; color: #10B981; font-weight: 600; margin-top: 8px; display: flex; align-items: center; gap: 6px;">
          <i class="bi bi-check-circle-fill"></i> {{ today_sales_count|default:0 }} ta savdo tranzaksiyasi
        </div>
      </div>
    </div>

    <!-- Card 2: Slaughter Yield -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <span style="font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;">So'yim Chiqimi (Yield)</span>
          <div style="width: 42px; height: 42px; border-radius: 14px; background: rgba(59,130,246,0.1); color: #3B82F6; display: flex; align-items: center; justify-content: center; font-size: 20px;">
            <i class="bi bi-pie-chart-fill"></i>
          </div>
        </div>
        <div style="font-size: 26px; font-weight: 800; color: #1A1A2E; letter-spacing: -0.5px;">
          {{ yield_percent|default:78 }}% <span style="font-size: 14px; color: #6B7280; font-weight: 500;">unumdorlik</span>
        </div>
        <div style="font-size: 12.5px; color: #3B82F6; font-weight: 600; margin-top: 8px;">
          <i class="bi bi-box-fill me-1"></i> {{ yield_processed|default:0|floatformat:1 }} kg toza go'sht olingan
        </div>
      </div>
    </div>

    <!-- Card 3: Customer Debts -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <span style="font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;">Umumiy Nasiya Qarzi</span>
          <div style="width: 42px; height: 42px; border-radius: 14px; background: rgba(239,68,68,0.1); color: #EF4444; display: flex; align-items: center; justify-content: center; font-size: 20px;">
            <i class="bi bi-journal-bookmark-fill"></i>
          </div>
        </div>
        <div style="font-size: 26px; font-weight: 800; color: #EF4444; letter-spacing: -0.5px;">
          {{ total_debt_amount|default:0|floatformat:0 }} <span style="font-size: 14px; color: #6B7280; font-weight: 500;">so'm</span>
        </div>
        <div style="font-size: 12.5px; color: #EF4444; font-weight: 600; margin-top: 8px;">
          <i class="bi bi-exclamation-triangle-fill me-1"></i> {{ top_debtors|length }} ta qarzdor mijozlar ro'yxati
        </div>
      </div>
    </div>

    <!-- Card 4: Inventory Stock -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <span style="font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px;">Ombor Zaxirasi</span>
          <div style="width: 42px; height: 42px; border-radius: 14px; background: rgba(245,158,11,0.1); color: #F59E0B; display: flex; align-items: center; justify-content: center; font-size: 20px;">
            <i class="bi bi-box2-fill"></i>
          </div>
        </div>
        <div style="font-size: 26px; font-weight: 800; color: #1A1A2E; letter-spacing: -0.5px;">
          {{ total_stock_qty|default:0|floatformat:1 }} <span style="font-size: 14px; color: #6B7280; font-weight: 500;">kg</span>
        </div>
        <div style="font-size: 12.5px; color: #F59E0B; font-weight: 600; margin-top: 8px;">
          <i class="bi bi-shield-fill-check me-1"></i> Mavjud tayyor va saralangan zaxira
        </div>
      </div>
    </div>
  </div>

  <!-- Manager Charts & AI Notifications Row -->
  <div class="row g-4">
    <!-- Chart Col -->
    <div class="col-lg-8">
      <div class="mfp-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div>
            <h5 class="m-0" style="font-family: 'DM Serif Display', serif; font-size: 20px; color: #1A1A2E;">
              Haftalik Nasiya & Qarz Risk dinamikasi
            </h5>
            <p style="margin: 4px 0 0; font-size: 12px; color: #6B7280;">Qarzlar qaytishi va yangi nasiya hajmi tendensiyasi</p>
          </div>
          <span class="badge bg-light text-dark font-monospace px-3 py-2" style="font-size: 11px; border: 1px solid rgba(0,0,0,0.08);">Mon - Sun</span>
        </div>
        <div style="height: 300px; position: relative;">
          <canvas id="debtTrendChart"></canvas>
        </div>
      </div>
    </div>

    <!-- AI Insights Col -->
    <div class="col-lg-4">
      <div class="mfp-card">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 36px; height: 36px; border-radius: 12px; background: rgba(212,168,83,0.15); color: #D4A853; display: flex; align-items: center; justify-content: center; font-size: 18px;">
              <i class="bi bi-robot"></i>
            </div>
            <h5 class="m-0" style="font-family: 'DM Serif Display', serif; font-size: 20px; color: #1A1A2E;">AI Qassob Tahlili</h5>
          </div>
          <span class="badge bg-warning bg-opacity-10 text-dark fw-bold" style="font-size: 10px;">PRO AI</span>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 14px;">
          {% for alert in ai_alerts %}
          <div style="background: #F8F6F2; border-radius: 14px; padding: 14px 16px; font-size: 13px; color: #1A1A2E; border-left: 4px solid {% if alert.level == 'danger' %}#EF4444{% elif alert.level == 'warning' %}#F59E0B{% else %}#10B981{% endif %}; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            {{ alert.text|safe }}
          </div>
          {% empty %}
          <div style="background: #F9FAFB; border-radius: 14px; padding: 16px; text-align: center; color: #6B7280; font-size: 13px;">
            <i class="bi bi-check-circle text-success font-24 mb-2 d-block"></i>
            Barcha ombor va kassa ko'rsatkichlari me'yorda!
          </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>

</div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('debtTrendChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: {{ week_days|safe }},
                datasets: [{
                    label: "Nasiya Qarz (ming so'm)",
                    data: {{ debt_trend|safe }},
                    borderColor: '#EF4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.08)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 3,
                    pointBackgroundColor: '#EF4444'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: 'rgba(0,0,0,0.04)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // Dynamic greeting based on time of day
    const hour = new Date().getHours();
    const grElem = document.getElementById('dynamic-greeting');
    if (grElem) {
        if (hour >= 5 && hour < 12) grElem.textContent = "Xayrli tong";
        else if (hour >= 12 && hour < 18) grElem.textContent = "Xayrli kun";
        else grElem.textContent = "Xayrli kech";
    }
});
</script>

{% else %}
'''

with open('templates/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Target specifically where customer landing page begins
target_token = "SARXIL GO'SHT LANDING PAGE"
if target_token in content:
    # Find the {% else %} preceding this token
    token_pos = content.find(target_token)
    else_pos = content.rfind('{% else %}', 0, token_pos)
    
    if else_pos != -1:
        customer_part = content[else_pos:]
        
        # Clean up any garbled characters in customer_part comment
        customer_part = customer_part.replace("в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ", "========================================================================")
        customer_part = customer_part.replace("в”Ђв”Ђ", "----------------")
        
        with open('templates/home.html', 'w', encoding='utf-8') as f:
            f.write(new_admin_part + customer_part[len('{% else %}'):])
        print("PRECISE_SUCCESS")
    else:
        print("ELSE_NOT_FOUND_BEFORE_TOKEN")
else:
    print("TARGET_TOKEN_NOT_FOUND")
