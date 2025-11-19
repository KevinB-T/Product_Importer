import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("product_importer")

app.config_from_object("django.conf:settings", namespace="CELERY")

# auto-discover tasks from all apps
app.autodiscover_tasks()
