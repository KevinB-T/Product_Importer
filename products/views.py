from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import ImportForm, ProductForm
from .models import ImportJob, Product
from .tasks import process_import_job


@require_POST
def bulk_delete_products(request):
    """
    STORY 3 – Bulk Delete from UI.

    Deletes all products in one DB-level operation.
    Protected by a confirmation dialog in the UI.
    """
    try:
        deleted_count, _ = Product.objects.all().delete()
        messages.success(request, f"Deleted {deleted_count} products.")
    except Exception as exc:
        messages.error(request, f"Failed to delete products: {exc!s}")
    return redirect("product_list")


class ProductCreateView(CreateView):
    """
    STORY 2 – Create a product via UI.
    """
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("product_list")


class ProductUpdateView(UpdateView):
    """
    STORY 2 – Update a product via UI.
    """
    model = Product
    form_class = ProductForm
    template_name = "products/product_form.html"
    success_url = reverse_lazy("product_list")


class ProductDeleteView(DeleteView):
    """
    STORY 2 – Delete a product via UI (with confirmation template).
    """
    model = Product
    template_name = "products/product_confirm_delete.html"
    success_url = reverse_lazy("product_list")


def upload_view(request):
    """
    STORY 1 – File Upload via UI.

    - Accepts a CSV upload.
    - Creates an ImportJob.
    - Offloads heavy CSV processing to Celery.
    - Redirects to a status page that will poll a JSON API.
    """
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            job = ImportJob.objects.create(
                original_filename=uploaded_file.name,
                status=ImportJob.STATUS_PENDING,
                file=uploaded_file,
            )
            # Asynchronous background processing – avoids 30s web timeouts.
            process_import_job.delay(str(job.id))
            return redirect("import_status", job_id=job.id)
    else:
        form = ImportForm()

    return render(request, "products/upload.html", {"form": form})


def import_status(request, job_id):
    """
    Renders the HTML status page (progress bar, etc.).
    """
    job = get_object_or_404(ImportJob, pk=job_id)
    return render(request, "products/import_status.html", {"job": job})


def import_status_api(request, job_id):
    """
    STORY 1A – Upload Progress Visibility (polled via JS).

    Returns live JSON that the frontend uses to update progress bar & status.
    """
    job = get_object_or_404(ImportJob, pk=job_id)

    return JsonResponse(
        {
            "status": job.status,
            "total_rows": job.total_rows,
            "processed_rows": job.processed_rows,
            "progress": job.progress_percent,
            "error_message": job.error_message,
        }
    )


def product_list(request):
    """
    STORY 2 – Product Management UI (list + filters + pagination).
    """
    qs = Product.objects.all().order_by("sku")

    q_sku = request.GET.get("sku")
    q_name = request.GET.get("name")
    q_desc = request.GET.get("description")
    q_active = request.GET.get("active")  # "true"/"false"/""/None

    if q_sku:
        qs = qs.filter(sku__icontains=q_sku)
    if q_name:
        qs = qs.filter(name__icontains=q_name)
    if q_desc:
        qs = qs.filter(description__icontains=q_desc)
    if q_active in ["true", "false"]:
        qs = qs.filter(is_active=(q_active == "true"))

    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q_sku": q_sku or "",
        "q_name": q_name or "",
        "q_desc": q_desc or "",
        "q_active": q_active or "",
    }
    return render(request, "products/product_list.html", context)
