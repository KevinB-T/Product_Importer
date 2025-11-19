from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import WebhookForm
from .models import Webhook, WebhookDelivery
from .tasks import send_test_webhook


class WebhookListView(ListView):
    model = Webhook
    template_name = "webhooks/webhook_list.html"
    context_object_name = "object_list"
    paginate_by = 50

    def get_queryset(self):
        return Webhook.objects.order_by("-created_at")


class WebhookCreateView(CreateView):
    model = Webhook
    form_class = WebhookForm
    template_name = "webhooks/webhook_form.html"
    success_url = reverse_lazy("webhook_list")


class WebhookUpdateView(UpdateView):
    model = Webhook
    form_class = WebhookForm
    template_name = "webhooks/webhook_form.html"
    success_url = reverse_lazy("webhook_list")


class WebhookDeleteView(DeleteView):
    model = Webhook
    template_name = "webhooks/webhook_confirm_delete.html"
    success_url = reverse_lazy("webhook_list")


def webhook_test(request, pk):
    """
    STORY 4 – Trigger a test webhook without blocking the request.
    """
    webhook = get_object_or_404(Webhook, pk=pk)
    send_test_webhook.delay(webhook.id)
    messages.info(request, "Test webhook triggered. Check deliveries for result.")
    return redirect("webhook_list")


def webhook_deliveries(request, pk):
    """
    Show latest deliveries for a given webhook.
    """
    webhook = get_object_or_404(Webhook, pk=pk)
    deliveries = webhook.deliveries.all()[:50]
    return render(
        request,
        "webhooks/webhook_deliveries.html",
        {"webhook": webhook, "deliveries": deliveries},
    )
