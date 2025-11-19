from django.db import models


class Webhook(models.Model):
    EVENT_CHOICES = [
        ("product.created", "Product Created"),
        ("product.updated", "Product Updated"),
        ("product.deleted", "Product Deleted"),
        ("import.completed", "Import Completed"),
    ]

    url = models.URLField()
    event = models.CharField(max_length=64, choices=EVENT_CHOICES)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["event", "is_enabled"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event} -> {self.url}"


class WebhookDelivery(models.Model):
    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    status_code = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-triggered_at",)

    def __str__(self) -> str:
        return f"Delivery #{self.pk} for {self.webhook_id}"
