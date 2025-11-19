import csv
import logging
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper
from typing import Dict, Iterable, List

from celery import shared_task
from django.db import transaction
from django.db.models.functions import Lower

from .models import ImportJob, Product
from webhooks.tasks import trigger_event_webhooks

logger = logging.getLogger(__name__)

# Tune this depending on DB power / deployment limits.
CHUNK_SIZE = 5000


@shared_task
def process_import_job(job_id: str) -> None:
    """
    Background CSV import.

    - Streams the uploaded file without loading 500k rows into memory.
    - Upserts products in chunks using bulk_create / bulk_update.
    - Treats SKU as case-insensitive and keeps it globally unique.
    """
    job = ImportJob.objects.get(pk=job_id)

    # Reset progress (useful if we ever support retries).
    job.status = ImportJob.STATUS_PROCESSING
    job.error_message = ""
    job.total_rows = 0
    job.processed_rows = 0
    job.save(update_fields=["status", "error_message", "total_rows", "processed_rows"])

    try:
        if not job.file:
            raise ValueError("No file associated with this import job.")

        # Stream the CSV as text; this is memory-efficient for large files.
        with job.file.open("rb") as f:
            wrapper = TextIOWrapper(f, encoding="utf-8", newline="")
            reader = csv.DictReader(wrapper)

            buffer: List[Dict[str, object]] = []

            for idx, row in enumerate(reader, start=1):
                # Let the UI see total rows grow so percentage is meaningful.
                job.total_rows = idx
                if idx % 1000 == 0:
                    job.save(update_fields=["total_rows"])

                normalized = _normalize_row(row)
                if not normalized:
                    # Skip rows without a valid SKU.
                    continue

                buffer.append(normalized)

                if len(buffer) >= CHUNK_SIZE:
                    _upsert_products(buffer, job)
                    buffer.clear()

            # Flush any remaining rows.
            if buffer:
                _upsert_products(buffer, job)

        job.status = ImportJob.STATUS_COMPLETED
        job.save(update_fields=["status", "processed_rows", "total_rows"])

        # Fire "import.completed" webhooks asynchronously.
        trigger_event_webhooks(
            event="import.completed",
            payload={
                "job_id": str(job.id),
                "filename": job.original_filename,
                "total_rows": job.total_rows,
                "processed_rows": job.processed_rows,
                "status": job.status,
            },
        )

    except Exception as exc:
        logger.exception("Import job %s failed", job_id)
        job.status = ImportJob.STATUS_FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        # Let Celery mark the task as failed.
        raise


def _normalize_row(row: Dict[str, str]) -> Dict[str, object] | None:
    """
    Normalize a CSV row into an internal representation for _upsert_products.

    Returns None for rows that should be skipped (e.g., missing SKU).
    """
    raw_sku = (row.get("sku") or "").strip()
    if not raw_sku:
        return None

    sku_upper = raw_sku.upper()
    name = (row.get("name") or "").strip()
    description = (row.get("description") or "").strip()

    raw_price = (row.get("price") or "").strip()
    if not raw_price:
        price = Decimal("0")
    else:
        try:
            price = Decimal(raw_price)
        except (InvalidOperation, TypeError):
            price = Decimal("0")

    return {
        "sku_upper": sku_upper,
        "name": name,
        "description": description,
        "price": price,
    }


def _upsert_products(buffer: Iterable[Dict[str, object]], job: ImportJob) -> None:
    """
    Bulk upsert Product rows for a buffer of normalized dicts.

    - SKUs are normalized to upper-case for storage.
    - Uses a single query to fetch existing records (case-insensitive).
    - Splits into bulk_create (new) & bulk_update (existing).
    - DOES NOT touch `is_active` on existing rows (UI controls that).
    """
    items = list(buffer)
    if not items:
        return

    # Unique lower-cased SKUs for querying existing rows.
    sku_lowers = {item["sku_upper"].lower() for item in items}

    existing_qs = (
        Product.objects
        .annotate(sku_lower=Lower("sku"))
        .filter(sku_lower__in=sku_lowers)
    )
    existing_by_lower = {p.sku.lower(): p for p in existing_qs}

    to_create: List[Product] = []
    to_update: List[Product] = []

    for item in items:
        key = item["sku_upper"].lower()
        existing = existing_by_lower.get(key)

        if existing:
            # Overwrite main fields but preserve is_active.
            existing.name = item["name"]
            existing.description = item["description"]
            existing.price = item["price"]
            to_update.append(existing)
        else:
            to_create.append(
                Product(
                    sku=item["sku_upper"],
                    name=item["name"],
                    description=item["description"],
                    price=item["price"],
                    # is_active defaults to True
                )
            )

    with transaction.atomic():
        if to_create:
            Product.objects.bulk_create(to_create, batch_size=1000)

        if to_update:
            Product.objects.bulk_update(
                to_update,
                fields=["name", "description", "price", "updated_at"],
                batch_size=1000,
            )

        job.processed_rows = job.processed_rows + len(items)
        job.save(update_fields=["processed_rows"])
