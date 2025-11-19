from django import forms
from .models import Product


class ImportForm(forms.Form):
    file = forms.FileField(
        label="Product CSV file",
        help_text=(
            "Upload a UTF-8 CSV containing columns like "
            "sku, name, description, price, is_active."
        ),
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".csv",
            }
        ),
    )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "description", "price", "is_active"]
        widgets = {
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Unique SKU (e.g. PROD-001)",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional description...",
                    "rows": 3,
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }
        labels = {
            "sku": "SKU",
            "name": "Name",
            "description": "Description",
            "price": "Price",
            "is_active": "Active?",
        }
        help_texts = {
            "sku": "Used to uniquely identify the product.",
            "is_active": "Uncheck to hide this product from active listings.",
        }
