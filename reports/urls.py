from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index_view, name='index'),
    path('pdf/', views.export_pdf_view, name='export_pdf'),
    path('excel/', views.export_excel_view, name='export_excel'),
]
