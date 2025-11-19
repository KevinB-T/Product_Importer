from django.db import models
from django.db.models import UniqueConstraint, Index
from django.db.models.functions import Lower
import uuid


class Product(models.Model):
    """
    A single product in the catalog.

    SKU is treated as case-insensitive and is unique across all records.
    """

    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Ensure SKU is unique in a case-insensitive way.
            UniqueConstraint(
                Lower("sku"),
                name="uniq_product_sku_ci",
            )
        ]
        indexes = [
            # Helps lookups & upsert logic.
            Index(Lower("sku"), name="idx_product_sku_ci"),
            Index(fields=["name"]),
            Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class ImportJob(models.Model):
    """
    Tracks a single CSV import.

    The Celery worker updates `status`, `total_rows`, `processed_rows`, and
    `error_message` so the UI can poll and render a progress bar.
    """

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # Stored so the worker can stream from disk.
    file = models.FileField(upload_to="imports/", blank=True, null=True)

    class Meta:
        ordering = ("-uploaded_at",)

    @property
    def progress_percent(self) -> int:
        if self.total_rows <= 0:
            return 0
        return int(self.processed_rows * 100 / self.total_rows)
