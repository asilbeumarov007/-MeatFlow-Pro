import os
with open('config/settings.py', 'a', encoding='utf-8') as f:
    f.write('''

# ==========================================
# JAZZMIN ADMIN PANEL SETTINGS
# ==========================================
JAZZMIN_SETTINGS = {
    "site_title": "MeatFlow Pro",
    "site_header": "MeatFlow",
    "site_brand": "MeatFlow Pro",
    "welcome_sign": "MeatFlow boshqaruv paneliga xush kelibsiz",
    "copyright": "MeatFlow Pro Ltd",
    
    "topmenu_links": [
        {"name": "Bosh sahifa", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "POS Terminal", "url": "/pos/"},
    ],
    
    "show_sidebar": True,
    "navigation_expanded": True,
    
    "custom_css": "css/custom_admin.css",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-success",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
''')
print("Settings updated successfully.")
