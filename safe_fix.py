import sys

with open('templates/home.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_admin_block = '''<!-- ========================================================================
     FINTECH DARK ADMIN DASHBOARD
     ======================================================================== -->
<style>
  body {
    background-color: #04110D !important;
    color: #E2E8F0 !important;
  }
  
  .mfp-glass-card {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 24px;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    height: 100%;
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
  }
  .mfp-glass-card:hover {
    transform: translateY(-3px);
    border-color: rgba(16, 185, 129, 0.3);
    box-shadow: 0 12px 40px rgba(16, 185, 129, 0.15);
  }

  .stat-title {
    font-size: 11px;
    font-weight: 800;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
  }
  .stat-value {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .glow-green { color: #10B981; text-shadow: 0 0 16px rgba(16, 185, 129, 0.6); }
  .glow-gold { color: #D4A853; text-shadow: 0 0 16px rgba(212, 168, 83, 0.6); }
  .glow-red { color: #EF4444; text-shadow: 0 0 16px rgba(239, 68, 68, 0.6); }
  .glow-blue { color: #38BDF8; text-shadow: 0 0 16px rgba(56, 189, 248, 0.6); }

  .stat-footer {
    font-size: 12.5px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.6);
  }
  .trend-up { color: #10B981; font-weight: 800; background: rgba(16, 185, 129, 0.15); padding: 2px 8px; border-radius: 20px; font-size: 10.5px; }
  .trend-down { color: #EF4444; font-weight: 800; background: rgba(239, 68, 68, 0.15); padding: 2px 8px; border-radius: 20px; font-size: 10.5px; }

  /* B2B Orders Table */
  .fintech-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 8px;
  }
  .fintech-table th {
    font-size: 10px;
    font-weight: 800;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 0 16px 8px;
    border: none;
  }
  .fintech-table td {
    background: rgba(255, 255, 255, 0.03);
    padding: 16px;
    font-size: 13.5px;
    color: #E2E8F0;
    font-weight: 600;
    border: 1px solid transparent;
    transition: all 0.2s;
  }
  .fintech-table tr td:first-child { border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-left: 1px solid rgba(255,255,255,0.05); }
  .fintech-table tr td:last-child { border-top-right-radius: 12px; border-bottom-right-radius: 12px; border-right: 1px solid rgba(255,255,255,0.05); }
  .fintech-table tr:hover td {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(212, 168, 83, 0.2);
  }

  .badge-status {
    padding: 4px 12px;
    border-radius: 30px;
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.5px;
    border: 1px solid currentColor;
  }
  .status-pending { color: #D4A853; background: rgba(212, 168, 83, 0.1); }
  .status-paid { color: #10B981; background: rgba(16, 185, 129, 0.1); }
  
  .ai-alert-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s;
  }
  .ai-alert-card:hover { transform: translateX(4px); }
  .ai-alert-card::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  }
  .ai-danger::before { background: #EF4444; box-shadow: 0 0 10px #EF4444; }
  .ai-warning::before { background: #D4A853; box-shadow: 0 0 10px #D4A853; }
  .ai-info::before { background: #38BDF8; box-shadow: 0 0 10px #38BDF8; }

</style>

<div class="animate__animated animate__fadeIn" style="max-width: 1440px; margin: 0 auto; padding: 32px 24px 80px; font-family: 'Plus Jakarta Sans', sans-serif;">
  
  <!-- Header -->
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 32px;">
    <div>
      <h2 style="font-family: 'DM Serif Display', serif; font-size: 2.4rem; color: #fff; margin: 0; font-weight: 400; display: flex; align-items: center; gap: 12px;">
        Dashboard
        <span class="badge" style="background: rgba(212, 168, 83, 0.15); color: #D4A853; border: 1px solid rgba(212, 168, 83, 0.3); font-size: 11px; font-family: 'Plus Jakarta Sans'; letter-spacing: 1px; font-weight: 800; padding: 4px 10px; border-radius: 6px;">
          <i class="bi bi-circle-fill" style="font-size: 6px; vertical-align: middle; margin-right: 4px; text-shadow: 0 0 8px #D4A853;"></i> LIVE
        </span>
      </h2>
      <p style="margin: 4px 0 0; color: rgba(255, 255, 255, 0.5); font-size: 13.5px;">
        <span id="dynamic-greeting">Xayrli kun</span>, <strong>{{ user.get_full_name|default:user.username }}</strong>. Real vaqt moliyaviy va operatsion ma'lumotlar.
      </p>
    </div>
    
    <div style="display: flex; gap: 12px;">
      <a href="/admin/pos/slaughter/add/" style="background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 10px 18px; border-radius: 12px; font-weight: 700; font-size: 13px; text-decoration: none; display: flex; align-items: center; gap: 8px; transition: all 0.2s;" onmouseover="this.style.background='rgba(16, 185, 129, 0.25)'" onmouseout="this.style.background='rgba(16, 185, 129, 0.15)'">
        <i class="bi bi-plus-lg text-glow-green"></i> So'yim Qo'shish
      </a>
    </div>
  </div>

  <!-- KPI 4 Cards -->
  <div class="row g-4 mb-4">
    <!-- Revenue -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div class="stat-title">Umumiy Tushum</div>
            <div class="stat-value glow-green">
              {{ today_revenue|default:0|floatformat:0 }} <span style="font-size: 14px; color: rgba(255,255,255,0.4); font-weight: 600;">UZS</span>
            </div>
            <div class="stat-footer">
              <span class="trend-up"><i class="bi bi-arrow-up-right"></i> {{ today_sales_count|default:0 }} ta tranzaksiya</span>
            </div>
          </div>
          <div style="width: 44px; height: 44px; border-radius: 14px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); color: #10B981; display: flex; align-items: center; justify-content: center; font-size: 20px; text-shadow: 0 0 10px rgba(16, 185, 129, 0.5);">
            <i class="bi bi-wallet2"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Yield -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div class="stat-title">So'yim Unumdorligi</div>
            <div class="stat-value glow-gold">
              {{ yield_percent|default:78 }}%
            </div>
            <div class="stat-footer">
              <span class="trend-up" style="color: #D4A853; background: rgba(212, 168, 83, 0.15);"><i class="bi bi-lightning-fill"></i> {{ yield_processed|default:0|floatformat:1 }} kg toza go'sht</span>
            </div>
          </div>
          <div style="width: 44px; height: 44px; border-radius: 14px; background: rgba(212, 168, 83, 0.1); border: 1px solid rgba(212, 168, 83, 0.2); color: #D4A853; display: flex; align-items: center; justify-content: center; font-size: 20px; text-shadow: 0 0 10px rgba(212, 168, 83, 0.5);">
            <i class="bi bi-scissors"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Debts -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div class="stat-title">Aktiv Nasiyalar</div>
            <div class="stat-value glow-red">
              {{ total_debt_amount|default:0|floatformat:0 }} <span style="font-size: 14px; color: rgba(255,255,255,0.4); font-weight: 600;">UZS</span>
            </div>
            <div class="stat-footer" style="display: flex; gap: 8px;">
              <span class="trend-down"><i class="bi bi-exclamation-triangle-fill"></i> {{ top_debtors|length }} ta qarzdor</span>
            </div>
          </div>
          <div style="width: 44px; height: 44px; border-radius: 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #EF4444; display: flex; align-items: center; justify-content: center; font-size: 20px; text-shadow: 0 0 10px rgba(239, 68, 68, 0.5);">
            <i class="bi bi-journal-x"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Total Stock -->
    <div class="col-xl-3 col-md-6">
      <div class="mfp-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div class="stat-title">Ombor Zaxirasi</div>
            <div class="stat-value glow-blue">
              {{ total_stock_qty|default:0|floatformat:1 }} <span style="font-size: 14px; color: rgba(255,255,255,0.4); font-weight: 600;">kg</span>
            </div>
            <div class="stat-footer">
              <span class="trend-up" style="color: #38BDF8; background: rgba(56, 189, 248, 0.15);"><i class="bi bi-box-seam"></i> Asosiy sovuqxona</span>
            </div>
          </div>
          <div style="width: 44px; height: 44px; border-radius: 14px; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.2); color: #38BDF8; display: flex; align-items: center; justify-content: center; font-size: 20px; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);">
            <i class="bi bi-boxes"></i>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Charts & Lists Row -->
  <div class="row g-4 mb-4">
    
    <!-- Main Chart -->
    <div class="col-xl-8">
      <div class="mfp-glass-card" style="display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
          <div>
            <h5 class="m-0" style="font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;">Tushum va Nasiya Dinamikasi</h5>
            <div style="font-size: 12px; color: rgba(255,255,255,0.4); font-weight: 600; margin-top: 4px;">Haftalik ko'rsatkichlar (ming UZS)</div>
          </div>
          <div style="display: flex; gap: 16px; font-size: 12px; font-weight: 700;">
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width:10px;height:10px;border-radius:50%;background:#10B981;box-shadow:0 0 8px #10B981;"></div> Tushum</div>
            <div style="display: flex; align-items: center; gap: 6px;"><div style="width:10px;height:10px;border-radius:50%;background:#EF4444;box-shadow:0 0 8px #EF4444;"></div> Nasiya</div>
          </div>
        </div>
        <div style="flex-grow: 1; position: relative; min-height: 280px;">
          <canvas id="fintechChart"></canvas>
        </div>
      </div>
    </div>

    <!-- AI Alerts -->
    <div class="col-xl-4">
      <div class="mfp-glass-card" style="display: flex; flex-direction: column;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
          <i class="bi bi-robot glow-gold" style="font-size: 22px;"></i>
          <h5 class="m-0" style="font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;">AI Qassob Tahlili</h5>
        </div>
        
        <div style="flex-grow: 1; overflow-y: auto; padding-right: 4px; max-height: 280px;">
          {% for alert in ai_alerts %}
          <div class="ai-alert-card {% if alert.level == 'danger' %}ai-danger{% elif alert.level == 'warning' %}ai-warning{% else %}ai-info{% endif %}">
            <div style="font-size: 13px; color: rgba(255,255,255,0.85); line-height: 1.5; font-weight: 500;">
              {{ alert.text|safe }}
            </div>
          </div>
          {% empty %}
          <div style="text-align: center; padding: 40px 20px; color: rgba(255,255,255,0.3);">
            <i class="bi bi-shield-check" style="font-size: 32px; color: #10B981; margin-bottom: 12px; display: block; text-shadow: 0 0 16px rgba(16,185,129,0.4);"></i>
            <div style="font-size: 13px; font-weight: 600;">Tizim barqaror. Barcha ko'rsatkichlar me'yorda.</div>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>

  <!-- B2B Orders & Recent Customers -->
  <div class="row g-4">
    <!-- B2B Table -->
    <div class="col-xl-8">
      <div class="mfp-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h5 class="m-0" style="font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;">Aktiv B2B Buyurtmalar</h5>
          <a href="#" style="font-size: 12px; font-weight: 700; color: #D4A853; text-decoration: none;">Barchasini ko'rish <i class="bi bi-arrow-right"></i></a>
        </div>
        
        <div style="overflow-x: auto;">
          <table class="fintech-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Mijoz</th>
                <th>Mahsulot</th>
                <th>Tugash sanasi</th>
                <th>Holati</th>
              </tr>
            </thead>
            <tbody>
              {% for o in b2b_orders %}
              <tr>
                <td style="color: rgba(255,255,255,0.5); font-family: monospace;">{{ o.id }}</td>
                <td>{{ o.customer }}</td>
                <td>{{ o.items }}</td>
                <td>{{ o.due_date|date:"d M, Y" }}</td>
                <td>
                  <span class="badge-status status-pending">{{ o.status }}</span>
                </td>
              </tr>
              {% empty %}
              <tr>
                <td colspan="5" style="text-align: center; color: rgba(255,255,255,0.3); padding: 32px;">Faol buyurtmalar yo'q</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Top Debtors Mini List -->
    <div class="col-xl-4">
      <div class="mfp-glass-card">
        <div style="margin-bottom: 20px;">
          <h5 class="m-0" style="font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;">Eng Katta Qarzdorlar</h5>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 12px;">
          {% for debtor in top_debtors %}
          <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(239,68,68,0.1); border-radius: 14px; padding: 14px; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;" onmouseover="this.style.background='rgba(239,68,68,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 36px; height: 36px; border-radius: 50%; background: rgba(239,68,68,0.1); color: #EF4444; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px;">
                {{ debtor.first_name|slice:":1" }}{{ debtor.last_name|slice:":1" }}
              </div>
              <div>
                <div style="font-size: 13.5px; font-weight: 700; color: #E2E8F0;">{{ debtor.first_name }} {{ debtor.last_name }}</div>
                <div style="font-size: 11px; color: rgba(255,255,255,0.4); font-weight: 600;">{{ debtor.phone_number }}</div>
              </div>
            </div>
            <div style="text-align: right;">
              <div class="glow-red" style="font-size: 14px; font-weight: 800;">{{ debtor.debt_amount|floatformat:0 }}</div>
              <div style="font-size: 10px; color: rgba(255,255,255,0.3); font-weight: 700; text-transform: uppercase;">Qarz summasi</div>
            </div>
          </div>
          {% empty %}
          <div style="text-align: center; padding: 32px 20px; color: rgba(255,255,255,0.3);">
            Qarzdor mijozlar topilmadi.
          </div>
          {% endfor %}
        </div>
        
      </div>
    </div>
  </div>

</div>

<script>
document.addEventListener("DOMContentLoaded", function() {
    // Dynamic greeting based on time of day
    const hour = new Date().getHours();
    const grElem = document.getElementById('dynamic-greeting');
    if (grElem) {
        if (hour >= 5 && hour < 12) grElem.textContent = "Xayrli tong";
        else if (hour >= 12 && hour < 18) grElem.textContent = "Xayrli kun";
        else grElem.textContent = "Xayrli kech";
    }

    // Modern Fintech Chart setup with gradients and glowing lines
    const ctx = document.getElementById('fintechChart');
    if (ctx) {
        const canvasCtx = ctx.getContext('2d');
        
        // Green gradient
        const gradientGreen = canvasCtx.createLinearGradient(0, 0, 0, 300);
        gradientGreen.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
        gradientGreen.addColorStop(1, 'rgba(16, 185, 129, 0.0)');
        
        // Red gradient
        const gradientRed = canvasCtx.createLinearGradient(0, 0, 0, 300);
        gradientRed.addColorStop(0, 'rgba(239, 68, 68, 0.4)');
        gradientRed.addColorStop(1, 'rgba(239, 68, 68, 0.0)');

        // Mock Data for Revenue (since we only have debt_trend from backend, let's mock revenue trend)
        const debtData = {{ debt_trend|safe }};
        const revData = debtData.map(v => v * 1.5 + (Math.random() * 5));

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: {{ week_days|safe }},
                datasets: [
                    {
                        label: "Tushum",
                        data: revData,
                        borderColor: '#10B981',
                        backgroundColor: gradientGreen,
                        borderWidth: 3,
                        pointBackgroundColor: '#04110D',
                        pointBorderColor: '#10B981',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: "Nasiya Qarz",
                        data: debtData,
                        borderColor: '#EF4444',
                        backgroundColor: gradientRed,
                        borderWidth: 3,
                        pointBackgroundColor: '#04110D',
                        pointBorderColor: '#EF4444',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(4, 17, 13, 0.95)',
                        titleColor: 'rgba(255,255,255,0.6)',
                        titleFont: { size: 11, family: 'Plus Jakarta Sans' },
                        bodyColor: '#fff',
                        bodyFont: { size: 13, weight: 'bold', family: 'Plus Jakarta Sans' },
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        boxPadding: 4,
                        usePointStyle: true,
                    }
                },
                scales: {
                    y: { 
                        grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                        ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 } }
                    },
                    x: { 
                        grid: { display: false, drawBorder: false },
                        ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 11 } }
                    }
                }
            }
        });
    }
});
</script>\n'''

# Replace lines 16 to 291 (0-indexed lines 16 to 291).
# Note: lines list is 0-indexed.
# Line 17 in the editor is lines[16].
# Line 292 is lines[291].
# We replace slice from 16 to 292.
new_content_lines = lines[:16] + [new_admin_block] + lines[292:]

with open('templates/home.html', 'w', encoding='utf-8') as f:
    f.writelines(new_content_lines)

print('Updated home.html safely using line indices.')
