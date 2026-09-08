from django.apps import AppConfig
from django.db.backends.signals import connection_created


def enable_sqlite_wal(sender, connection, **kwargs):
    """Enable SQLite WAL mode and optimizations for high concurrency."""
    if connection.vendor == 'sqlite':
        try:
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode=WAL;')
                cursor.execute('PRAGMA synchronous=NORMAL;')
                cursor.execute('PRAGMA cache_size=-64000;')  # 64MB Cache
                cursor.execute('PRAGMA busy_timeout=10000;') # 10s Timeout
        except Exception:
            pass


class PosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pos'

    def ready(self):
        connection_created.connect(enable_sqlite_wal)
