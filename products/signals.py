from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Product
from webhooks.tasks import trigger_event_webhooks


def _product_payload(instance: Product) -> dict:
    return {
        "sku": instance.sku,
        "name": instance.name,
        "description": instance.description,
        "price": str(instance.price),
        "is_active": instance.is_active,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
    }


@receiver(post_save, sender=Product)
def product_saved(sender, instance: Product, created: bool, **kwargs) -> None:
    """
    STORY 4 – Automatically trigger product.created / product.updated webhooks.
    """
    event = "product.created" if created else "product.updated"
    trigger_event_webhooks(event=event, payload={"event": event, "product": _product_payload(instance)})


@receiver(post_delete, sender=Product)
def product_deleted(sender, instance: Product, **kwargs) -> None:
    """
    STORY 4 – Automatically trigger product.deleted webhooks.
    """
    event = "product.deleted"
    trigger_event_webhooks(event=event, payload={"event": event, "product": _product_payload(instance)})
