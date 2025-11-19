from django.urls import path
from . import views

urlpatterns = [
    path("", views.WebhookListView.as_view(), name="webhook_list"),
    path("create/", views.WebhookCreateView.as_view(), name="webhook_create"),
    path("<int:pk>/edit/", views.WebhookUpdateView.as_view(), name="webhook_update"),
    path("<int:pk>/delete/", views.WebhookDeleteView.as_view(), name="webhook_delete"),
    path("<int:pk>/test/", views.webhook_test, name="webhook_test"),
    path("<int:pk>/deliveries/", views.webhook_deliveries, name="webhook_deliveries"),
]