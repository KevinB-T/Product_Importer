import logging
import time
from typing import Dict

import requests
from celery import shared_task
from django.utils import timezone

from .models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


@shared_task
def deliver_webhook(webhook_id: int, payload: Dict, event: str | None = None) -> None:
    """
    Send a webhook and record a WebhookDelivery.

    This runs in Celery, so HTTP latency does not block the main app.
    """
    webhook = Webhook.objects.get(pk=webhook_id)
    event = event or webhook.event

    delivery = WebhookDelivery.objects.create(
        webhook=webhook,
        success=False,
        error_message="",
    )

    t0 = time.time()
    try:
        r = requests.post(
            webhook.url,
            json={
                "event": event,
                "sent_at": timezone.now().isoformat(),
                "data": payload,
            },
            timeout=5,  # keep workers responsive
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        delivery.status_code = r.status_code
        delivery.response_time_ms = elapsed_ms
        delivery.success = r.ok
        delivery.error_message = "" if r.ok else r.text[:500]
        delivery.save()

    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook %s delivery failed: %s", webhook_id, exc)
        elapsed_ms = int((time.time() - t0) * 1000)
        delivery.status_code = None
        delivery.response_time_ms = elapsed_ms
        delivery.success = False
        delivery.error_message = str(exc)[:500]
        delivery.save()


@shared_task
def send_test_webhook(webhook_id: int) -> None:
    """
    Celery task used by the UI “Test” button.
    """
    webhook = Webhook.objects.get(pk=webhook_id)
    payload = {
        "type": "test",
        "message": "Test webhook from Product Importer",
    }
    deliver_webhook.delay(webhook.id, payload, event=webhook.event)


def trigger_event_webhooks(event: str, payload: Dict) -> None:
    """
    Called from the products app (signals and import task).

    Finds all enabled webhooks for `event` and queues deliveries.
    """
    qs = Webhook.objects.filter(event=event, is_enabled=True)
    for webhook in qs:
        deliver_webhook.delay(webhook.id, payload, event=event)
