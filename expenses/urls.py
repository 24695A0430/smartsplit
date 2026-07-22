from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('create/<int:group_id>/', views.expense_create_view, name='create'),
    path('<int:expense_id>/', views.expense_detail_view, name='detail'),
    path('<int:expense_id>/edit/', views.expense_edit_view, name='edit'),
    path('<int:expense_id>/delete/', views.expense_delete_view, name='delete'),
]
