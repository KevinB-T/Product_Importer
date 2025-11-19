from django import forms
from .models import Webhook


class WebhookForm(forms.ModelForm):
    class Meta:
        model = Webhook
        fields = ["url", "event", "is_enabled"]
        widgets = {
            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/webhooks/products",
                }
            ),
            "event": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "is_enabled": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }
        labels = {
            "url": "Destination URL",
            "event": "Event type",
            "is_enabled": "Enabled?",
        }
        help_texts = {
            "url": "We will POST the webhook payload to this URL.",
            "event": "Choose which event should trigger this webhook.",
            "is_enabled": "Disable to temporarily stop sending requests.",
        }
