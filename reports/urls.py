from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_page, name="report_commessa"),
    path("api/kairos/", views.kairos_dataset, name="kairos_dataset"),
    path("api/excel/", views.excel_dataset, name="excel_dataset"),
    path("api/prescrizioni/<int:employee_id>/", views.save_prescriptions, name="save_prescriptions"),
]
