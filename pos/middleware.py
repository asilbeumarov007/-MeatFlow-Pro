# pos/middleware.py
from django.utils.deprecation import MiddlewareMixin
from .translit import convert_html_to_cyrillic


class UzbekScriptMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Faqat HTML sahifalarni va muvaffaqiyatli yuklangan (200) javoblarni qayta ishlaymiz
        if response.status_code == 200 and "text/html" in response.get("Content-Type", ""):
            # Sessiyadan qaysi alifbo tanlanganini tekshiramiz (defolt: latin)
            script_mode = request.session.get('script_mode', 'latin')

            if script_mode == 'cyrillic':
                content = response.content.decode('utf-8')
                converted_content = convert_html_to_cyrillic(content)
                response.content = converted_content.encode('utf-8')

        return response