from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_view, name="upload"),
    path("upload/<uuid:job_id>/status/", views.import_status, name="import_status"),
    path("api/import/<uuid:job_id>/", views.import_status_api, name="import_status_api"),
    path("", views.product_list, name="product_list"),
    path("create/", views.ProductCreateView.as_view(), name="product_create"),
    path("<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_update"),
    path("<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("bulk-delete/", views.bulk_delete_products, name="bulk_delete_products"),
]